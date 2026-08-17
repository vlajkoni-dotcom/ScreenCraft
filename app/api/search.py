from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database.db import get_db
from app.models.movie import Movie
from app.models.show import Show
from app.models.user_content import UserContent
from app.schemas.common import ContentTypeAPI
from app.schemas.search import SearchCandidate, SearchResponse
from app.services.tmdb import tmdb_client

router = APIRouter(prefix="/api/search", tags=["search"])


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except ValueError:
        return None


@router.get("", response_model=SearchResponse)
async def search(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    """
    Globalna pretraga - koristi TMDB /search/multi (serije + filmovi u jednom pozivu).
    Za svaki rezultat proverava da li je već u ličnoj biblioteci i sa kojim statusom.
    """
    raw_results = await tmdb_client.search_multi(q)

    # Skupi tmdb_id-jeve po tipu da uradimo jedan DB upit umesto N upita
    show_tmdb_ids = [r["id"] for r in raw_results if r["media_type"] == "tv"]
    movie_tmdb_ids = [r["id"] for r in raw_results if r["media_type"] == "movie"]

    shows_in_db: dict[int, Show] = {}
    if show_tmdb_ids:
        result = await db.execute(select(Show).where(Show.tmdb_id.in_(show_tmdb_ids)))
        shows_in_db = {s.tmdb_id: s for s in result.scalars().all()}

    movies_in_db: dict[int, Movie] = {}
    if movie_tmdb_ids:
        result = await db.execute(select(Movie).where(Movie.tmdb_id.in_(movie_tmdb_ids)))
        movies_in_db = {m.tmdb_id: m for m in result.scalars().all()}

    local_show_ids = [s.id for s in shows_in_db.values()]
    local_movie_ids = [m.id for m in movies_in_db.values()]

    status_by_show: dict[int, str] = {}
    status_by_movie: dict[int, str] = {}
    if local_show_ids:
        result = await db.execute(
            select(UserContent).where(
                UserContent.content_type == ContentTypeAPI.SHOW.value,
                UserContent.content_id.in_(local_show_ids),
            )
        )
        status_by_show = {uc.content_id: uc.status for uc in result.scalars().all()}
    if local_movie_ids:
        result = await db.execute(
            select(UserContent).where(
                UserContent.content_type == ContentTypeAPI.MOVIE.value,
                UserContent.content_id.in_(local_movie_ids),
            )
        )
        status_by_movie = {uc.content_id: uc.status for uc in result.scalars().all()}

    candidates: list[SearchCandidate] = []
    for r in raw_results:
        if r["media_type"] == "tv":
            local = shows_in_db.get(r["id"])
            candidates.append(
                SearchCandidate(
                    content_type=ContentTypeAPI.SHOW,
                    tmdb_id=r["id"],
                    title=r.get("name", ""),
                    original_title=r.get("original_name"),
                    year=_year_from_date(r.get("first_air_date")),
                    overview=r.get("overview"),
                    poster_path=r.get("poster_path"),
                    vote_average=r.get("vote_average"),
                    popularity=r.get("popularity"),
                    already_in_library=local is not None,
                    current_status=status_by_show.get(local.id) if local else None,
                )
            )
        else:
            local = movies_in_db.get(r["id"])
            candidates.append(
                SearchCandidate(
                    content_type=ContentTypeAPI.MOVIE,
                    tmdb_id=r["id"],
                    title=r.get("title", ""),
                    original_title=r.get("original_title"),
                    year=_year_from_date(r.get("release_date")),
                    overview=r.get("overview"),
                    poster_path=r.get("poster_path"),
                    vote_average=r.get("vote_average"),
                    popularity=r.get("popularity"),
                    already_in_library=local is not None,
                    current_status=status_by_movie.get(local.id) if local else None,
                )
            )

    return SearchResponse(query=q, results=candidates)
