from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.content_common import ShowAiringStatus, TimestampMixin
from app.models.genre import show_genres
from app.models.person import show_cast


class Show(Base, TimestampMixin):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Eksterni identifikatori - bar jedan mora postojati, oba se koriste za sync
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    tvmaze_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_air_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    airing_status: Mapped[str] = mapped_column(
        String(32), default=ShowAiringStatus.UNKNOWN.value, nullable=False
    )

    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    vote_average: Mapped[float | None] = mapped_column(nullable=True)
    popularity: Mapped[float | None] = mapped_column(nullable=True)

    # Vremenski žig poslednjeg uspešnog sync-a metapodataka/epizoda za ovu seriju
    last_synced_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    genres = relationship("Genre", secondary=show_genres, back_populates="shows")
    cast = relationship("Person", secondary=show_cast, back_populates="shows")
    seasons: Mapped[list["Season"]] = relationship(
        "Season", back_populates="show", cascade="all, delete-orphan"
    )
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode", back_populates="show", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Show {self.title} ({self.first_air_date})>"


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"), index=True)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    show: Mapped["Show"] = relationship("Show", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship("Episode", back_populates="season")

    def __repr__(self) -> str:
        return f"<Season {self.show_id} S{self.season_number}>"
