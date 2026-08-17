from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Osiguraj da folder za SQLite fajl postoji (npr. ./data/)
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency - daje DB sesiju po requestu."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Kreira sve tabele ako ne postoje. Za V1 dovoljno umesto pune migracione alatke."""
    # Uvozimo sve modele da SQLAlchemy metadata zna za njih pre create_all.
    from app.models import (  # noqa: F401
        content_common,
        episode,
        genre,
        movie,
        person,
        provider,
        settings as settings_model,
        show,
        sync_log,
        user_content,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
