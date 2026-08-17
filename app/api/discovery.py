from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.services.discovery import (
    discover_new_movies,
    discover_new_seasons_suggestions,
    discover_new_series,
    get_genre_filter_options,
    get_movie_genre_filter_options,
    get_new_seasons_for_library,
    get_provider_filter_options,
)
from app.services.tmdb import TMDBError

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.get("/new-seasons")
async def new_seasons(db: AsyncSession = Depends(get_db)):
    return await get_new_seasons_for_library(db)


@router.get("/new-seasons/suggestions")
async def new_seasons_suggestions(window: str = "next_30", db: AsyncSession = Depends(get_db)):
    try:
        return await discover_new_seasons_suggestions(db, window=window)
    except (TMDBError, HTTPStatusError) as e:
        raise HTTPException(status_code=502, detail=f"TMDB nije dostupan ili API ključ nije važeći: {e}")


@router.get("/new-series")
async def new_series(
    window: str = "next_30",
    genre_id: int | None = None,
    provider_id: int | None = None,
):
    try:
        return await discover_new_series(window=window, genre_id=genre_id, provider_id=provider_id)
    except (TMDBError, HTTPStatusError) as e:
        raise HTTPException(status_code=502, detail=f"TMDB nije dostupan ili API ključ nije važeći: {e}")


@router.get("/new-movies")
async def new_movies(window: str = "last_30", genre_id: int | None = None):
    try:
        return await discover_new_movies(window=window, genre_id=genre_id)
    except (TMDBError, HTTPStatusError) as e:
        raise HTTPException(status_code=502, detail=f"TMDB nije dostupan ili API ključ nije važeći: {e}")


@router.get("/filters")
async def filters():
    """Žanrovi i platforme za filter kontrole - direktno sa TMDB-a, ne hardkodovano."""
    try:
        tv_genres = await get_genre_filter_options()
        movie_genres = await get_movie_genre_filter_options()
        providers = await get_provider_filter_options()
    except (TMDBError, HTTPStatusError) as e:
        raise HTTPException(status_code=502, detail=f"TMDB nije dostupan ili API ključ nije važeći: {e}")
    return {"tv_genres": tv_genres, "movie_genres": movie_genres, "providers": providers}
