from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.services.calendar import get_calendar_events

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
async def calendar(year: int | None = None, month: int | None = None, db: AsyncSession = Depends(get_db)):
    today = date.today()
    year = year or today.year
    month = month or today.month
    events = await get_calendar_events(db, year, month)
    return {"year": year, "month": month, "events": events}
