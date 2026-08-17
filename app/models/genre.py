from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

# Many-to-many asocijacije: jedan žanr (npr. "Sci-Fi") pripada mnogim serijama/filmovima
show_genres = Table(
    "show_genres",
    Base.metadata,
    Column("show_id", ForeignKey("shows.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # TMDB ima svoj fiksni genre ID - čuvamo ga radi lakšeg mapiranja pri sync-u
    tmdb_genre_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    shows = relationship("Show", secondary=show_genres, back_populates="genres")
    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")

    def __repr__(self) -> str:
        return f"<Genre {self.name}>"
