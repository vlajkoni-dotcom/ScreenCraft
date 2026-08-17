from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings as get_env_settings
from app.database.db import get_db
from app.models.settings import AppSetting

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    region: str
    timezone: str
    tmdb_api_key_configured: bool


class SettingsUpdate(BaseModel):
    region: str | None = None
    timezone: str | None = None


async def _get_setting(db: AsyncSession, key: str, default: str) -> str:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


@router.get("", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    env = get_env_settings()
    region = await _get_setting(db, "region", env.default_region)
    tz = await _get_setting(db, "timezone", env.default_timezone)
    return SettingsOut(
        region=region,
        timezone=tz,
        tmdb_api_key_configured=bool(env.tmdb_api_key),
    )


@router.post("", response_model=SettingsOut)
async def update_settings(payload: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    if payload.region:
        await _upsert(db, "region", payload.region)
    if payload.timezone:
        await _upsert(db, "timezone", payload.timezone)
    await db.commit()
    return await get_settings(db)


async def _upsert(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
