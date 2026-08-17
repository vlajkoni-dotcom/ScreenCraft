from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db import get_db
from app.models.movie import Movie
from app.models.provider import Availability, Provider
from app.models.show import Season, Show
from app.schemas.common import ContentTypeAPI
from app.schemas.content import (
    EpisodeOut,
    MovieDetailOut,
    ProviderOut,
    SeasonOut,
    SetStatusRequest,
    ShowDetailOut,
)
from app.models.user_content import WatchedEpisode
from app.services.library import (
    ensure_tvmaze_link,
    get_or_create_movie,
    get_or_create_show,
    get_user_content_status,
    set_user_content_status,
    sync_show_episodes,
)

router = APIRouter(prefix="/api", tags=["content"])


async def _get_providers_out(
    db: AsyncSession, content_type: ContentTypeAPI, content_id: int
) -> list[ProviderOut]:
    result = await db.execute(
        select(Availability, Provider)
        .join(Provider, Availability.provider_id == Provider.id)
        .where(
            Availability.content_type == content_type.value,
            Availability.content_id == content_id,
        )
    )
    out = []
    for availability, provider in result.all():
        out.append(
            ProviderOut(
                name=provider.name,
                logo_path=provider.logo_path,
                offer_type=availability.offer_type,
                country_code=availability.country_code,
            )
        )
    return out


@router.get("/shows/{tmdb_id}", response_model=ShowDetailOut)
async def get_show_detail(tmdb_id: int, db: AsyncSession = Depends(get_db)):
    """
    Dohvata (ili prvi put kreira iz TMDB-a) seriju po TMDB ID-u, sa sezonama,
    epizodama i streaming dostupnošću. Ako epizode još nisu sinhronizovane
    sa TVmaze-om, radi to odmah (lazy sync na prvi pristup).
    """
    try:
        show = await get_or_create_show(db, tmdb_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = await db.execute(select(Show).where(Show.id == show.id).options(
        selectinload(Show.seasons).selectinload(Season.episodes), selectinload(Show.genres)
    ))
    show = result.scalar_one()

    if not show.seasons:
        show = await ensure_tvmaze_link(db, show)
        await sync_show_episodes(db, show)
        result = await db.execute(select(Show).where(Show.id == show.id).options(
            selectinload(Show.seasons).selectinload(Season.episodes), selectinload(Show.genres)
        ))
        show = result.scalar_one()

    providers = await _get_providers_out(db, ContentTypeAPI.SHOW, show.id)
    user_content = await get_user_content_status(db, ContentTypeAPI.SHOW, show.id)

    watched_episode_ids: set[int] = set()
    if user_content:
        watched_result = await db.execute(
            select(WatchedEpisode.episode_id).where(WatchedEpisode.user_content_id == user_content.id)
        )
        watched_episode_ids = {row[0] for row in watched_result.all()}

    seasons_out = []
    for s in sorted(show.seasons, key=lambda s: s.season_number):
        episodes_out = [
            EpisodeOut.model_validate(e).model_copy(update={"watched": e.id in watched_episode_ids})
            for e in sorted(s.episodes, key=lambda e: e.episode_number)
        ]
        # Sezona je "fully watched" samo ako ima bar jednu epizodu i SVE su gledane -
        # prazna sezona (bez epizoda, npr. najavljena ali još nema podataka) se ne broji.
        fully_watched = bool(episodes_out) and all(e.watched for e in episodes_out)
        seasons_out.append(
            SeasonOut(
                id=s.id,
                season_number=s.season_number,
                episode_count=s.episode_count,
                air_date=s.air_date,
                episodes=episodes_out,
                fully_watched=fully_watched,
            )
        )

    return ShowDetailOut(
        id=show.id,
        tmdb_id=show.tmdb_id,
        tvmaze_id=show.tvmaze_id,
        title=show.title,
        original_title=show.original_title,
        first_air_date=show.first_air_date,
        airing_status=show.airing_status,
        overview=show.overview,
        poster_path=show.poster_path,
        backdrop_path=show.backdrop_path,
        vote_average=show.vote_average,
        genres=[g.name for g in show.genres],
        seasons=seasons_out,
        providers=providers,
        user_status=user_content.status if user_content else None,
    )


@router.get("/movies/{tmdb_id}", response_model=MovieDetailOut)
async def get_movie_detail(tmdb_id: int, db: AsyncSession = Depends(get_db)):
    try:
        movie = await get_or_create_movie(db, tmdb_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = await db.execute(
        select(Movie).where(Movie.id == movie.id).options(selectinload(Movie.genres))
    )
    movie = result.scalar_one()

    providers = await _get_providers_out(db, ContentTypeAPI.MOVIE, movie.id)
    user_content = await get_user_content_status(db, ContentTypeAPI.MOVIE, movie.id)

    return MovieDetailOut(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        title=movie.title,
        original_title=movie.original_title,
        release_date=movie.release_date,
        runtime_minutes=movie.runtime_minutes,
        overview=movie.overview,
        poster_path=movie.poster_path,
        backdrop_path=movie.backdrop_path,
        vote_average=movie.vote_average,
        genres=[g.name for g in movie.genres],
        providers=providers,
        user_status=user_content.status if user_content else None,
    )


@router.post("/shows/{tmdb_id}/resync")
async def resync_show_episodes(tmdb_id: int, db: AsyncSession = Depends(get_db)):
    """
    Ručno pokreće ponovnu sinhronizaciju epizoda sa TVmaze-a - sigurnosna mreža
    ako automatski sync na prvom pristupu ne uspe (npr. privremen mrežni problem).
    """
    try:
        show = await get_or_create_show(db, tmdb_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    show = await ensure_tvmaze_link(db, show)
    updated = await sync_show_episodes(db, show)
    return {"tmdb_id": tmdb_id, "tvmaze_id": show.tvmaze_id, "episodes_synced": updated}


@router.post("/shows/{tmdb_id}/status")
async def set_show_status(tmdb_id: int, payload: SetStatusRequest, db: AsyncSession = Depends(get_db)):
    try:
        show = await get_or_create_show(db, tmdb_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    uc = await set_user_content_status(
        db, ContentTypeAPI.SHOW, show.id, payload.status, payload.personal_rating, payload.notes
    )
    return {"content_type": "show", "content_id": show.id, "status": uc.status}


@router.post("/movies/{tmdb_id}/status")
async def set_movie_status(tmdb_id: int, payload: SetStatusRequest, db: AsyncSession = Depends(get_db)):
    try:
        movie = await get_or_create_movie(db, tmdb_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    uc = await set_user_content_status(
        db, ContentTypeAPI.MOVIE, movie.id, payload.status, payload.personal_rating, payload.notes
    )
    return {"content_type": "movie", "content_id": movie.id, "status": uc.status}
