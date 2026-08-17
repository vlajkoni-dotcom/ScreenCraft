from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.content_common import TimestampMixin
from app.models.genre import movie_genres
from app.models.person import movie_cast


class Movie(Base, TimestampMixin):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    # TVmaze ne pokriva filmove - IMDB id čuvamo radi budućih izvora (npr. JustWatch po IMDB id-u)
    imdb_id: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backdrop_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    vote_average: Mapped[float | None] = mapped_column(nullable=True)
    popularity: Mapped[float | None] = mapped_column(nullable=True)

    last_synced_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    genres = relationship("Genre", secondary=movie_genres, back_populates="movies")
    cast = relationship("Person", secondary=movie_cast, back_populates="movies")

    def __repr__(self) -> str:
        return f"<Movie {self.title} ({self.release_date})>"
