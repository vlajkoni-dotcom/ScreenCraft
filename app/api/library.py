from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.episode import Episode
from app.models.user_content import UserContent, WatchedEpisode
from app.schemas.common import ContentTypeAPI
from app.services.dashboard import (
    get_library_by_status,
    get_next_episodes,
    get_today_episodes,
    get_watching_with_progress,
)

router = APIRouter(prefix="/api/library", tags=["library"])

VALID_STATUSES = {"watching", "watchlist", "watched", "dropped", "paused", "not_interested"}


@router.get("/status/{status}")
async def library_by_status(status: str, content_type: str | None = None, db: AsyncSession = Depends(get_db)):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Nepoznat status: {status}")
    return await get_library_by_status(db, status, content_type)


@router.get("/watching")
async def watching_with_progress(db: AsyncSession = Depends(get_db)):
    return await get_watching_with_progress(db)


@router.get("/today")
async def today(db: AsyncSession = Depends(get_db)):
    return await get_today_episodes(db)


@router.get("/next-episodes")
async def next_episodes(db: AsyncSession = Depends(get_db)):
    return await get_next_episodes(db)


@router.post("/seasons/{season_id}/watched")
async def mark_season_watched(season_id: int, db: AsyncSession = Depends(get_db)):
    """Označava SVE epizode date sezone kao gledane odjednom."""
    result = await db.execute(select(Episode).where(Episode.season_id == season_id))
    episodes = result.scalars().all()
    if not episodes:
        raise HTTPException(status_code=404, detail="Sezona nema epizoda ili ne postoji.")

    show_id = episodes[0].show_id
    result = await db.execute(
        select(UserContent).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.content_id == show_id,
        )
    )
    user_content = result.scalar_one_or_none()
    if not user_content:
        raise HTTPException(
            status_code=400,
            detail="Serija nije u tvojoj biblioteci - dodaj je (npr. WATCHING) pre nego što označiš epizode.",
        )

    existing = await db.execute(
        select(WatchedEpisode.episode_id).where(WatchedEpisode.user_content_id == user_content.id)
    )
    already_watched = {row[0] for row in existing.all()}

    now = datetime.now(timezone.utc)
    for ep in episodes:
        if ep.id not in already_watched:
            db.add(WatchedEpisode(user_content_id=user_content.id, episode_id=ep.id, watched_at=now))

    await db.commit()
    return {"season_id": season_id, "marked_episodes": len(episodes)}
async def mark_episode_watched(episode_id: int, db: AsyncSession = Depends(get_db)):
    """
    Označava epizodu kao gledanu. Traži postojeći UserContent zapis (serija mora
    već biti u WATCHING/WATCHLIST) - ne kreira ga automatski da ne bismo tiho
    dodavali serije u biblioteku kroz sporedan endpoint.
    """
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Epizoda nije pronađena.")

    result = await db.execute(
        select(UserContent).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.content_id == episode.show_id,
        )
    )
    user_content = result.scalar_one_or_none()
    if not user_content:
        raise HTTPException(
            status_code=400,
            detail="Serija nije u tvojoj biblioteci - dodaj je (npr. WATCHING) pre nego što označiš epizode.",
        )

    existing = await db.execute(
        select(WatchedEpisode).where(
            WatchedEpisode.user_content_id == user_content.id,
            WatchedEpisode.episode_id == episode_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            WatchedEpisode(
                user_content_id=user_content.id,
                episode_id=episode_id,
                watched_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    return {"episode_id": episode_id, "watched": True}


@router.delete("/episodes/{episode_id}/watched")
async def unmark_episode_watched(episode_id: int, db: AsyncSession = Depends(get_db)):
    """Skida oznaku 'gledano' sa epizode (npr. slučajan klik)."""
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Epizoda nije pronađena.")

    result = await db.execute(
        select(UserContent).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.content_id == episode.show_id,
        )
    )
    user_content = result.scalar_one_or_none()
    if not user_content:
        return {"episode_id": episode_id, "watched": False}

    await db.execute(
        WatchedEpisode.__table__.delete().where(
            WatchedEpisode.user_content_id == user_content.id,
            WatchedEpisode.episode_id == episode_id,
        )
    )
    await db.commit()
    return {"episode_id": episode_id, "watched": False}
