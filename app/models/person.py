from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

show_cast = Table(
    "show_cast",
    Base.metadata,
    Column("show_id", ForeignKey("shows.id", ondelete="CASCADE"), primary_key=True),
    Column("person_id", ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(32), primary_key=True),  # "actor" | "creator" | "director"
)

movie_cast = Table(
    "movie_cast",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("person_id", ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(32), primary_key=True),
)


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_person_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    shows = relationship("Show", secondary=show_cast, back_populates="cast")
    movies = relationship("Movie", secondary=movie_cast, back_populates="cast")

    def __repr__(self) -> str:
        return f"<Person {self.name}>"
