from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.services.recommendations import get_recommendations
from app.services.tmdb import TMDBError

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
async def recommendations(limit: int = 10, db: AsyncSession = Depends(get_db)):
    try:
        return await get_recommendations(db, limit=limit)
    except (TMDBError, HTTPStatusError) as e:
        raise HTTPException(status_code=502, detail=f"TMDB nije dostupan ili API ključ nije važeći: {e}")
