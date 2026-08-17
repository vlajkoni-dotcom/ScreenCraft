from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class SyncLog(Base):
    """Evidencija svakog background sync pokušaja - izvor, trajanje, rezultat, greške."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # "tmdb" | "tvmaze"
    task: Mapped[str] = mapped_column(String(64), nullable=False)  # npr. "episodes_sync"

    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded lista grešaka

    def __repr__(self) -> str:
        return f"<SyncLog {self.source}/{self.task} @ {self.started_at}>"
