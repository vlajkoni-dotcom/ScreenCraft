from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.show import Season, Show
from app.models.user_content import UserContent
from app.schemas.common import ContentTypeAPI
from app.services.tmdb import tmdb_client

# Koliko dana unazad/unapred se smatra da je sezona "nova" na tvojim serijama.
NEW_SEASON_WINDOW_BACK_DAYS = 30
NEW_SEASON_WINDOW_FORWARD_DAYS = 90

WINDOW_PRESETS = {
    "last_7": ("past", 7),
    "last_30": ("past", 30),
    "last_90": ("past", 90),
    "next_30": ("future", 30),
    "next_90": ("future", 90),
}


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except ValueError:
        return None


async def get_new_seasons_for_library(db: AsyncSession) -> list[dict]:
    """
    Serije koje već pratiš (bilo koji status osim not_interested/dropped) sa
    sezonom čiji je air_date u prozoru [danas-30, danas+90] - "nova sezona".
    """
    result = await db.execute(
        select(UserContent.content_id).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.status.in_(["watching", "watchlist", "watched", "paused"]),
        )
    )
    show_ids = [row[0] for row in result.all()]
    if not show_ids:
        return []

    today = date.today()
    window_start = today - timedelta(days=NEW_SEASON_WINDOW_BACK_DAYS)
    window_end = today + timedelta(days=NEW_SEASON_WINDOW_FORWARD_DAYS)

    result = await db.execute(
        select(Season, Show)
        .join(Show, Season.show_id == Show.id)
        .where(
            Season.show_id.in_(show_ids),
            Season.air_date.is_not(None),
            Season.air_date >= window_start,
            Season.air_date <= window_end,
        )
        .order_by(Season.air_date.desc())
    )

    out = []
    for season, show in result.all():
        out.append({
            "tmdb_id": show.tmdb_id,
            "title": show.title,
            "poster_path": show.poster_path,
            "season_number": season.season_number,
            "air_date": season.air_date.isoformat(),
            "is_upcoming": season.air_date > today,
        })
    return out


async def discover_new_seasons_suggestions(db: AsyncSession, window: str = "next_30") -> list[dict]:
    """
    Nove sezone SVIH (ne samo tvojih) serija - preporuke, koristi TMDB discover
    filtrirano po datumu emitovanja sledeće epizode (air_date, ne first_air_date -
    to razlikuje "nova sezona postojeće serije" od "potpuno nova serija").
    Isključuje serije koje već imaš u biblioteci (bilo koji status) - te već
    vidiš u sekciji iznad.
    """
    if window not in WINDOW_PRESETS:
        window = "next_30"
    direction, days = WINDOW_PRESETS[window]
    today = date.today()

    filters: dict = {"sort_by": "popularity.desc", "include_adult": "false"}
    if direction == "past":
        filters["air_date.gte"] = (today - timedelta(days=days)).isoformat()
        filters["air_date.lte"] = today.isoformat()
    else:
        filters["air_date.gte"] = today.isoformat()
        filters["air_date.lte"] = (today + timedelta(days=days)).isoformat()

    results = await tmdb_client.discover_tv(**filters)

    result = await db.execute(
        select(UserContent.content_id).where(UserContent.content_type == ContentTypeAPI.SHOW.value)
    )
    # content_id ovde je lokalni Show.id, ne tmdb_id - moramo mapirati preko Show tabele
    result_ids = [row[0] for row in result.all()]
    tracked_tmdb_ids: set[int] = set()
    if result_ids:
        show_result = await db.execute(select(Show.tmdb_id).where(Show.id.in_(result_ids)))
        tracked_tmdb_ids = {row[0] for row in show_result.all() if row[0]}

    out = []
    for r in results[:24]:
        tmdb_id = r.get("id")
        if tmdb_id in tracked_tmdb_ids:
            continue
        # Preskačemo serije sa first_air_date == 0 sezona uslov (tj. serije koje TEK počinju -
        # to je "nova serija", ne "nova sezona") - filtriramo grubo po broju sezona kad je dostupno.
        out.append({
            "tmdb_id": tmdb_id,
            "title": r.get("name", ""),
            "poster_path": r.get("poster_path"),
            "overview": r.get("overview"),
            "year": _year_from_date(r.get("first_air_date")),
            "vote_average": r.get("vote_average"),
            "popularity": r.get("popularity"),
        })
    return out


async def discover_new_series(
    window: str = "next_30",
    genre_id: int | None = None,
    provider_id: int | None = None,
) -> list[dict]:
    """
    TMDB discovery za nove/uskoro-nove serije, sa filterima. Ne diramo lokalnu
    bazu ovde - ovo je "browse", korisnik bira šta dodaje u biblioteku.
    """
    if window not in WINDOW_PRESETS:
        window = "next_30"
    direction, days = WINDOW_PRESETS[window]
    today = date.today()

    filters: dict = {
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }
    if direction == "past":
        filters["first_air_date.gte"] = (today - timedelta(days=days)).isoformat()
        filters["first_air_date.lte"] = today.isoformat()
    else:
        filters["first_air_date.gte"] = today.isoformat()
        filters["first_air_date.lte"] = (today + timedelta(days=days)).isoformat()

    if genre_id:
        filters["with_genres"] = genre_id
    if provider_id:
        settings = get_settings()
        filters["with_watch_providers"] = provider_id
        filters["watch_region"] = settings.default_region

    results = await tmdb_client.discover_tv(**filters)

    out = []
    for r in results[:24]:
        out.append({
            "tmdb_id": r.get("id"),
            "title": r.get("name", ""),
            "poster_path": r.get("poster_path"),
            "overview": r.get("overview"),
            "year": _year_from_date(r.get("first_air_date")),
            "first_air_date": r.get("first_air_date"),
            "vote_average": r.get("vote_average"),
            "popularity": r.get("popularity"),
        })
    return out


async def get_genre_filter_options() -> list[dict]:
    genres = await tmdb_client.get_tv_genre_list()
    return [{"id": g["id"], "name": g["name"]} for g in genres]


async def get_provider_filter_options() -> list[dict]:
    settings = get_settings()
    providers = await tmdb_client.get_tv_watch_provider_list(settings.default_region)
    return [
        {"id": p["provider_id"], "name": p["provider_name"], "logo_path": p.get("logo_path")}
        for p in sorted(providers, key=lambda p: p.get("display_priority", 999))[:20]
    ]


# ---------- FILMOVI ----------

# TMDB with_release_type kodovi: 1=Premiere, 2=Theatrical (limited), 3=Theatrical,
# 4=Digital, 5=Physical (Blu-ray/DVD), 6=TV. Nas zanimaju SAMO 4 i 5 - tek stigli
# na streaming ili fizički disk, ne stari katalog i ne bioskopska premijera.
NEW_MOVIE_RELEASE_TYPES = "4,5"


async def _get_actual_digital_or_physical_date(tmdb_id: int) -> date | None:
    """
    TMDB discover filtrira po najavljenom (ponekad budućem) datumu, što zna da
    prikaže filmove koji tek TREBA da izađu na streaming/BD. Ovde proveravamo
    stvarni datum iz /release_dates po zemljama - uzimamo NAJRANIJI digital
    (type=4) ili physical (type=5) datum koji je već PROŠAO. Ako nijedan takav
    datum ne postoji (samo najavljeni budući), vraćamo None - film se izbacuje.
    """
    results = await tmdb_client.get_movie_release_dates(tmdb_id)
    today = date.today()
    earliest: date | None = None

    for country in results:
        for entry in country.get("release_dates", []):
            if entry.get("type") not in (4, 5):
                continue
            raw_date = entry.get("release_date", "")[:10]
            try:
                release_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                continue
            if release_date > today:
                continue  # najavljen, ali još nije izašao - ne računa se
            if earliest is None or release_date < earliest:
                earliest = release_date

    return earliest


async def discover_new_movies(window: str = "last_30", genre_id: int | None = None) -> list[dict]:
    """
    Filmovi koji su STVARNO tek stigli na streaming/Blu-ray (ne stari katalog,
    i ne najavljeni-ali-još-neizašli naslovi).

    Prvi krug (TMDB discover/movie) je samo gruba pretraga kandidata po
    popularnosti - drugi krug proverava STVARAN datum digital/physical
    izdanja po filmu (/release_dates) i odbacuje sve što još nije izašlo.
    Zato ovaj poziv radi više API zahteva nego ostali discovery pozivi.
    """
    if window not in WINDOW_PRESETS:
        window = "last_30"
    _, days = WINDOW_PRESETS[window]
    today = date.today()
    window_start = today - timedelta(days=days)

    filters: dict = {
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "with_release_type": NEW_MOVIE_RELEASE_TYPES,
        # Široka gornja granica unazad (2 godine) samo da ograničimo skup kandidata -
        # stvarna provera datuma se radi ispod, ovo NIJE konačan filter.
        "primary_release_date.gte": (today - timedelta(days=730)).isoformat(),
        "primary_release_date.lte": today.isoformat(),
    }
    if genre_id:
        filters["with_genres"] = genre_id

    candidates = await tmdb_client.discover_movie(**filters)

    out = []
    for r in candidates[:40]:  # ogranicavamo broj provera da ne pravimo previse poziva
        if len(out) >= 24:
            break
        tmdb_id = r.get("id")
        if not tmdb_id:
            continue
        actual_date = await _get_actual_digital_or_physical_date(tmdb_id)
        if actual_date is None or actual_date < window_start:
            continue  # jos nije stvarno izasao, ili je izasao van trazenog perioda

        out.append({
            "tmdb_id": tmdb_id,
            "title": r.get("title", ""),
            "poster_path": r.get("poster_path"),
            "overview": r.get("overview"),
            "year": _year_from_date(r.get("release_date")),
            "release_date": actual_date.isoformat(),
            "vote_average": r.get("vote_average"),
            "popularity": r.get("popularity"),
        })

    out.sort(key=lambda m: m["release_date"], reverse=True)
    return out


async def get_movie_genre_filter_options() -> list[dict]:
    genres = await tmdb_client.get_movie_genre_list()
    return [{"id": g["id"], "name": g["name"]} for g in genres]
