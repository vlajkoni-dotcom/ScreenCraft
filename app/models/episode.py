from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), index=True)

    tvmaze_episode_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    tmdb_episode_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Schedule polja - TVmaze je primarni izvor (vidi services/sync.py)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    air_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    schedule_source: Mapped[str] = mapped_column(String(16), default="tvmaze", nullable=False)

    show: Mapped["Show"] = relationship("Show", back_populates="episodes")
    season: Mapped["Season"] = relationship("Season", back_populates="episodes")

    def __repr__(self) -> str:
        return f"<Episode show={self.show_id} S{self.season_number:02d}E{self.episode_number:02d}>"
