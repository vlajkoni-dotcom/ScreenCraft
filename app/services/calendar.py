import calendar as calendar_module
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode
from app.models.show import Show
from app.models.user_content import UserContent
from app.schemas.common import ContentTypeAPI
from app.services.tmdb import tmdb_client


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar_module.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


async def get_tracked_episodes(db: AsyncSession, start: date, end: date) -> list[dict]:
    """Epizode serija koje pratis (WATCHING/WATCHLIST) - glavni sloj kalendara."""
    result = await db.execute(
        select(UserContent.content_id).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.status.in_(["watching", "watchlist"]),
        )
    )
    show_ids = [row[0] for row in result.all()]
    if not show_ids:
        return []

    result = await db.execute(
        select(Episode, Show)
        .join(Show, Episode.show_id == Show.id)
        .where(
            Episode.show_id.in_(show_ids),
            Episode.air_date.is_not(None),
            Episode.air_date >= start,
            Episode.air_date <= end,
        )
    )
    out = []
    for episode, show in result.all():
        out.append({
            "type": "episode",
            "date": episode.air_date.isoformat(),
            "title": show.title,
            "subtitle": f"S{episode.season_number:02d}E{episode.episode_number:02d}"
                        + (f" - {episode.title}" if episode.title else ""),
            "tmdb_id": show.tmdb_id,
            "poster_path": show.poster_path,
        })
    return out


async def get_season_finales(db: AsyncSession, start: date, end: date) -> list[dict]:
    """
    Finala sezona - za SVE serije koje vec postoje u lokalnoj bazi (bilo koji
    status, i one koje ne pratis), bez obzira na status pracenja. Finale =
    epizoda sa najvecim episode_number u svojoj sezoni (po podacima koje imamo).
    """
    result = await db.execute(
        select(Episode, Show)
        .join(Show, Episode.show_id == Show.id)
        .where(Episode.air_date.is_not(None), Episode.air_date >= start, Episode.air_date <= end)
    )
    candidates = result.all()
    if not candidates:
        return []

    season_ids = {ep.season_id for ep, _ in candidates}
    result = await db.execute(
        select(Episode.season_id, Episode.episode_number).where(Episode.season_id.in_(season_ids))
    )
    max_ep_by_season: dict[int, int] = {}
    for season_id, ep_number in result.all():
        max_ep_by_season[season_id] = max(max_ep_by_season.get(season_id, 0), ep_number)

    out = []
    for episode, show in candidates:
        if episode.episode_number == max_ep_by_season.get(episode.season_id) and episode.episode_number > 0:
            out.append({
                "type": "season_finale",
                "date": episode.air_date.isoformat(),
                "title": show.title,
                "subtitle": f"Season {episode.season_number} finale - S{episode.season_number:02d}E{episode.episode_number:02d}",
                "tmdb_id": show.tmdb_id,
                "poster_path": show.poster_path,
            })
    return out


async def get_new_seasons_month(start: date, end: date) -> list[dict]:
    """Nove sezone (bilo koje serije) cija je air_date u ovom mesecu - TMDB discover."""
    filters = {
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "air_date.gte": start.isoformat(),
        "air_date.lte": end.isoformat(),
    }
    results = await tmdb_client.discover_tv(**filters)
    out = []
    for r in results[:30]:
        out.append({
            "type": "new_season",
            "date": r.get("first_air_date") or start.isoformat(),
            "title": r.get("name", ""),
            "subtitle": "New season airing this month",
            "tmdb_id": r.get("id"),
            "poster_path": r.get("poster_path"),
        })
    return out


async def get_new_series_month(start: date, end: date) -> list[dict]:
    """Potpuno nove serije cija je first_air_date u ovom mesecu."""
    filters = {
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "first_air_date.gte": start.isoformat(),
        "first_air_date.lte": end.isoformat(),
    }
    results = await tmdb_client.discover_tv(**filters)
    out = []
    for r in results[:30]:
        out.append({
            "type": "new_series",
            "date": r.get("first_air_date") or start.isoformat(),
            "title": r.get("name", ""),
            "subtitle": "New series premiere",
            "tmdb_id": r.get("id"),
            "poster_path": r.get("poster_path"),
        })
    return out


async def get_calendar_events(db: AsyncSession, year: int, month: int) -> list[dict]:
    start, end = _month_bounds(year, month)

    tracked = await get_tracked_episodes(db, start, end)
    finales = await get_season_finales(db, start, end)

    new_seasons: list[dict] = []
    new_series: list[dict] = []
    try:
        new_seasons = await get_new_seasons_month(start, end)
        new_series = await get_new_series_month(start, end)
    except Exception:
        # TMDB-zavisni slojevi ne smeju da obore ceo kalendar - lokalni podaci
        # (tracked episodes, finales) i dalje rade cak i ako je TMDB nedostupan.
        pass

    all_events = tracked + finales + new_seasons + new_series
    all_events.sort(key=lambda e: e["date"])
    return all_events
