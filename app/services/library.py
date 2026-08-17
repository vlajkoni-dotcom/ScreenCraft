from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode
from app.models.genre import Genre
from app.models.movie import Movie
from app.models.provider import Availability, Provider
from app.models.show import Season, Show
from app.models.user_content import UserContent
from app.schemas.common import ContentTypeAPI
from app.services.tmdb import tmdb_client
from app.services.tvmaze import tvmaze_client


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


async def _get_or_create_genres(db: AsyncSession, tmdb_genres: list[dict]) -> list[Genre]:
    genres = []
    for g in tmdb_genres:
        result = await db.execute(select(Genre).where(Genre.tmdb_genre_id == g["id"]))
        genre = result.scalar_one_or_none()
        if genre is None:
            genre = Genre(tmdb_genre_id=g["id"], name=g["name"])
            db.add(genre)
            await db.flush()
        genres.append(genre)
    return genres


async def _upsert_availability(
    db: AsyncSession, content_type: ContentTypeAPI, content_id: int, tmdb_providers_by_country: dict
) -> None:
    """tmdb_providers_by_country je 'results' iz /watch/providers - ključ je country_code."""
    from app.config import get_settings

    settings = get_settings()
    country_data = tmdb_providers_by_country.get(settings.default_region)
    if not country_data:
        return  # nema podataka za Srbiju - ne izmišljamo, samo preskačemo

    offer_map = {
        "flatrate": country_data.get("flatrate", []),
        "rent": country_data.get("rent", []),
        "buy": country_data.get("buy", []),
        "free": country_data.get("free", []),
        "ads": country_data.get("ads", []),
    }
    for offer_type, providers in offer_map.items():
        for p in providers:
            result = await db.execute(
                select(Provider).where(Provider.tmdb_provider_id == p["provider_id"])
            )
            provider = result.scalar_one_or_none()
            if provider is None:
                provider = Provider(
                    tmdb_provider_id=p["provider_id"],
                    name=p["provider_name"],
                    logo_path=p.get("logo_path"),
                )
                db.add(provider)
                await db.flush()

            existing = await db.execute(
                select(Availability).where(
                    Availability.content_type == content_type.value,
                    Availability.content_id == content_id,
                    Availability.provider_id == provider.id,
                    Availability.country_code == settings.default_region,
                    Availability.offer_type == offer_type,
                )
            )
            if existing.scalar_one_or_none() is None:
                db.add(
                    Availability(
                        content_type=content_type.value,
                        content_id=content_id,
                        provider_id=provider.id,
                        country_code=settings.default_region,
                        offer_type=offer_type,
                        source="tmdb",
                    )
                )


async def get_or_create_show(db: AsyncSession, tmdb_id: int) -> Show:
    result = await db.execute(select(Show).where(Show.tmdb_id == tmdb_id))
    show = result.scalar_one_or_none()
    if show is not None:
        return show

    details = await tmdb_client.get_tv_details(tmdb_id)
    if not details:
        raise ValueError(f"TMDB tv/{tmdb_id} nije pronađen - ne mogu da napravim zapis.")

    show = Show(
        tmdb_id=tmdb_id,
        title=details.get("name", ""),
        original_title=details.get("original_name"),
        first_air_date=_parse_date(details.get("first_air_date")),
        airing_status=details.get("status", "Unknown"),
        overview=details.get("overview"),
        poster_path=details.get("poster_path"),
        backdrop_path=details.get("backdrop_path"),
        vote_average=details.get("vote_average"),
        popularity=details.get("popularity"),
        last_synced_at=datetime.now(timezone.utc).isoformat(),
    )
    show.genres = await _get_or_create_genres(db, details.get("genres", []))
    db.add(show)
    await db.flush()

    # Pokušaj da nađemo TVmaze zapis preko IMDB ID-a ako TMDB da external_ids
    # (V1: jednostavan search po nazivu kao fallback)
    tvmaze_matches = await tvmaze_client.search_shows(show.title)
    if tvmaze_matches:
        show.tvmaze_id = tvmaze_matches[0]["show"]["id"]

    providers = await tmdb_client.get_tv_watch_providers(tmdb_id)
    await _upsert_availability(db, ContentTypeAPI.SHOW, show.id, providers)

    await db.commit()
    await db.refresh(show)
    return show


async def get_or_create_movie(db: AsyncSession, tmdb_id: int) -> Movie:
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie = result.scalar_one_or_none()
    if movie is not None:
        return movie

    details = await tmdb_client.get_movie_details(tmdb_id)
    if not details:
        raise ValueError(f"TMDB movie/{tmdb_id} nije pronađen - ne mogu da napravim zapis.")

    movie = Movie(
        tmdb_id=tmdb_id,
        imdb_id=details.get("imdb_id"),
        title=details.get("title", ""),
        original_title=details.get("original_title"),
        release_date=_parse_date(details.get("release_date")),
        runtime_minutes=details.get("runtime"),
        overview=details.get("overview"),
        poster_path=details.get("poster_path"),
        backdrop_path=details.get("backdrop_path"),
        vote_average=details.get("vote_average"),
        popularity=details.get("popularity"),
        last_synced_at=datetime.now(timezone.utc).isoformat(),
    )
    movie.genres = await _get_or_create_genres(db, details.get("genres", []))
    db.add(movie)
    await db.flush()

    providers = await tmdb_client.get_movie_watch_providers(tmdb_id)
    await _upsert_availability(db, ContentTypeAPI.MOVIE, movie.id, providers)

    await db.commit()
    await db.refresh(movie)
    return movie


async def ensure_tvmaze_link(db: AsyncSession, show: Show) -> Show:
    """
    Ako serija nema tvmaze_id (npr. prvi pokušaj matchovanja nije uspeo zbog
    privremenog mrežnog problema), pokušava ponovo. Ne pada tiho - ako i dalje
    ne uspe, show ostaje bez tvmaze_id i sync_show_episodes će to preskočiti
    (nema šta da izmišljamo).
    """
    if show.tvmaze_id:
        return show

    matches = await tvmaze_client.search_shows(show.title)
    if matches:
        show.tvmaze_id = matches[0]["show"]["id"]
        await db.commit()
        await db.refresh(show)
    return show


async def sync_show_episodes(db: AsyncSession, show: Show) -> int:
    """Povuci sve sezone/epizode sa TVmaze-a (primarni schedule izvor). Vraća broj upisanih epizoda."""
    if not show.tvmaze_id:
        return 0

    tvmaze_episodes = await tvmaze_client.get_show_episodes(show.tvmaze_id)
    updated = 0
    seasons_by_number: dict[int, Season] = {}

    for ep in tvmaze_episodes:
        season_number = ep["season"]
        if season_number not in seasons_by_number:
            result = await db.execute(
                select(Season).where(Season.show_id == show.id, Season.season_number == season_number)
            )
            season = result.scalar_one_or_none()
            if season is None:
                season = Season(show_id=show.id, season_number=season_number)
                db.add(season)
                await db.flush()
            seasons_by_number[season_number] = season
        season = seasons_by_number[season_number]

        result = await db.execute(
            select(Episode).where(Episode.tvmaze_episode_id == ep["id"])
        )
        episode = result.scalar_one_or_none()
        air_time = None
        if ep.get("airtime"):
            try:
                air_time = datetime.strptime(ep["airtime"], "%H:%M").time()
            except ValueError:
                air_time = None

        if episode is None:
            episode = Episode(
                show_id=show.id,
                season_id=season.id,
                tvmaze_episode_id=ep["id"],
                season_number=season_number,
                episode_number=ep["number"] or 0,
                title=ep.get("name"),
                overview=ep.get("summary"),
                air_date=_parse_date(ep.get("airdate")),
                air_time=air_time,
                schedule_source="tvmaze",
            )
            db.add(episode)
            updated += 1
        else:
            episode.air_date = _parse_date(ep.get("airdate"))
            episode.air_time = air_time
            episode.title = ep.get("name")
            updated += 1

    await db.commit()
    return updated


async def get_user_content_status(
    db: AsyncSession, content_type: ContentTypeAPI, content_id: int
) -> UserContent | None:
    result = await db.execute(
        select(UserContent).where(
            UserContent.content_type == content_type.value,
            UserContent.content_id == content_id,
        )
    )
    return result.scalar_one_or_none()


async def set_user_content_status(
    db: AsyncSession,
    content_type: ContentTypeAPI,
    content_id: int,
    status: str,
    personal_rating: float | None = None,
    notes: str | None = None,
) -> UserContent:
    user_content = await get_user_content_status(db, content_type, content_id)
    now = datetime.now(timezone.utc)
    if user_content is None:
        user_content = UserContent(
            content_type=content_type.value,
            content_id=content_id,
            status=status,
            personal_rating=personal_rating,
            notes=notes,
            status_changed_at=now,
        )
        db.add(user_content)
    else:
        if user_content.status != status:
            user_content.status_changed_at = now
        user_content.status = status
        if personal_rating is not None:
            user_content.personal_rating = personal_rating
        if notes is not None:
            user_content.notes = notes

    await db.commit()
    await db.refresh(user_content)
    return user_content
