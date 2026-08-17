from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.episode import Episode
from app.models.movie import Movie
from app.models.show import Show
from app.models.user_content import UserContent, WatchedEpisode
from app.schemas.common import ContentTypeAPI


async def _shows_by_ids(db: AsyncSession, ids: list[int]) -> dict[int, Show]:
    if not ids:
        return {}
    result = await db.execute(select(Show).where(Show.id.in_(ids)))
    return {s.id: s for s in result.scalars().all()}


async def _movies_by_ids(db: AsyncSession, ids: list[int]) -> dict[int, Movie]:
    if not ids:
        return {}
    result = await db.execute(select(Movie).where(Movie.id.in_(ids)))
    return {m.id: m for m in result.scalars().all()}


async def get_library_by_status(
    db: AsyncSession, status: str, content_type: str | None = None
) -> list[dict]:
    """Vraća listu (show ili movie) sa datim korisničkim statusom - koristi se za
    Watching / Watchlist / Watched / Dropped / Paused / Not Interested stranice."""
    query = select(UserContent).where(UserContent.status == status)
    if content_type:
        query = query.where(UserContent.content_type == content_type)
    result = await db.execute(query.order_by(UserContent.updated_at.desc()))
    user_items = result.scalars().all()

    show_ids = [uc.content_id for uc in user_items if uc.content_type == ContentTypeAPI.SHOW.value]
    movie_ids = [uc.content_id for uc in user_items if uc.content_type == ContentTypeAPI.MOVIE.value]

    shows = await _shows_by_ids(db, show_ids)
    movies = await _movies_by_ids(db, movie_ids)

    out = []
    for uc in user_items:
        if uc.content_type == ContentTypeAPI.SHOW.value:
            show = shows.get(uc.content_id)
            if not show:
                continue
            out.append({
                "content_type": "show",
                "tmdb_id": show.tmdb_id,
                "title": show.title,
                "poster_path": show.poster_path,
                "year": show.first_air_date.year if show.first_air_date else None,
                "airing_status": show.airing_status,
                "status": uc.status,
                "personal_rating": uc.personal_rating,
            })
        else:
            movie = movies.get(uc.content_id)
            if not movie:
                continue
            out.append({
                "content_type": "movie",
                "tmdb_id": movie.tmdb_id,
                "title": movie.title,
                "poster_path": movie.poster_path,
                "year": movie.release_date.year if movie.release_date else None,
                "status": uc.status,
                "personal_rating": uc.personal_rating,
            })
    return out


async def get_watching_with_progress(db: AsyncSession) -> list[dict]:
    """Za WATCHING stranicu - svaka serija sa poslednjom gledanom i sledećom epizodom."""
    result = await db.execute(
        select(UserContent).where(
            UserContent.status == "watching",
            UserContent.content_type == ContentTypeAPI.SHOW.value,
        )
    )
    user_items = result.scalars().all()
    if not user_items:
        return []

    show_ids = [uc.content_id for uc in user_items]
    result = await db.execute(
        select(Show).where(Show.id.in_(show_ids)).options(selectinload(Show.episodes))
    )
    shows = {s.id: s for s in result.scalars().all()}

    out = []
    for uc in user_items:
        show = shows.get(uc.content_id)
        if not show:
            continue

        watched_result = await db.execute(
            select(WatchedEpisode.episode_id).where(WatchedEpisode.user_content_id == uc.id)
        )
        watched_episode_ids = {row[0] for row in watched_result.all()}

        all_episodes = sorted(show.episodes, key=lambda e: (e.season_number, e.episode_number))
        watched_eps = [e for e in all_episodes if e.id in watched_episode_ids]
        unwatched_eps = [e for e in all_episodes if e.id not in watched_episode_ids]

        last_watched = watched_eps[-1] if watched_eps else None
        next_episode = unwatched_eps[0] if unwatched_eps else None

        out.append({
            "content_type": "show",
            "tmdb_id": show.tmdb_id,
            "title": show.title,
            "poster_path": show.poster_path,
            "airing_status": show.airing_status,
            "current_season": next_episode.season_number if next_episode else (
                last_watched.season_number if last_watched else None
            ),
            "watched_count": len(watched_eps),
            "total_count": len(all_episodes),
            "last_watched": (
                f"S{last_watched.season_number:02d}E{last_watched.episode_number:02d}"
                if last_watched else None
            ),
            "next_episode": (
                {
                    "id": next_episode.id,
                    "code": f"S{next_episode.season_number:02d}E{next_episode.episode_number:02d}",
                    "title": next_episode.title,
                    "air_date": next_episode.air_date.isoformat() if next_episode.air_date else None,
                }
                if next_episode else None
            ),
        })
    return out


async def get_today_episodes(db: AsyncSession, days_ahead: int = 2) -> list[dict]:
    """Danas / Sutra / Prekosutra - epizode serija koje pratim (WATCHING ili WATCHLIST)."""
    result = await db.execute(
        select(UserContent.content_id).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.status.in_(["watching", "watchlist"]),
        )
    )
    show_ids = [row[0] for row in result.all()]
    if not show_ids:
        return []

    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    result = await db.execute(
        select(Episode, Show)
        .join(Show, Episode.show_id == Show.id)
        .where(
            Episode.show_id.in_(show_ids),
            Episode.air_date.is_not(None),
            Episode.air_date >= today,
            Episode.air_date <= end_date,
        )
        .order_by(Episode.air_date, Episode.air_time)
    )

    out = []
    for episode, show in result.all():
        out.append({
            "tmdb_id": show.tmdb_id,
            "title": show.title,
            "poster_path": show.poster_path,
            "code": f"S{episode.season_number:02d}E{episode.episode_number:02d}",
            "episode_title": episode.title,
            "air_date": episode.air_date.isoformat(),
            "air_time": episode.air_time.strftime("%H:%M") if episode.air_time else None,
            "day_label": (
                "Today" if episode.air_date == today
                else "Tomorrow" if episode.air_date == today + timedelta(days=1)
                else "In 2 days" if episode.air_date == today + timedelta(days=2)
                else episode.air_date.isoformat()
            ),
        })
    return out


async def get_next_episodes(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Sledeće (buduće) epizode serija koje pratim, hronološki - za Dashboard."""
    watching = await get_watching_with_progress(db)
    upcoming = [w for w in watching if w["next_episode"] and w["next_episode"]["air_date"]]
    upcoming.sort(key=lambda w: w["next_episode"]["air_date"])
    return upcoming[:limit]
