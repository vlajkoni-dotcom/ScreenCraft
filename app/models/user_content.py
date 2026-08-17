from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.content_common import TimestampMixin, UserContentStatus


class UserContent(Base, TimestampMixin):
    """
    Jedinstvena tabela za korisnikov odnos prema JEDNOJ stavci (serija ili film).

    Ovo zamenjuje odvojene 'user_shows' i 'watchlist' tabele iz prvobitnog
    predloga: watchlist je samo status=WATCHLIST ovde, da ne bismo imali dva
    izvora istine za isti podatak. 'position' polje postoji za ručno
    sortiranje watchliste ako ti ikad zatreba.
    """

    __tablename__ = "user_content"
    __table_args__ = (
        UniqueConstraint("content_type", "content_id", name="uq_user_content_unique_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    personal_rating: Mapped[float | None] = mapped_column(nullable=True)  # 0-10, tvoja ocena
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status_changed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    watched_episodes: Mapped[list["WatchedEpisode"]] = relationship(
        "WatchedEpisode", back_populates="user_content", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserContent {self.content_type}:{self.content_id} status={self.status}>"


class WatchedEpisode(Base):
    """
    Beleži da je epizoda gledana. Samo za serije (movies nemaju epizode -
    za film je dovoljan status=WATCHED na UserContent).

    Rewatch se namerno NE prati u V1 - jedan red po epizodi je dovoljan
    (unique constraint sprečava duplikate).
    """

    __tablename__ = "watched_episodes"
    __table_args__ = (
        UniqueConstraint("user_content_id", "episode_id", name="uq_watched_episode_once"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_content_id: Mapped[int] = mapped_column(
        ForeignKey("user_content.id", ondelete="CASCADE"), index=True
    )
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    watched_at: Mapped[datetime] = mapped_column(nullable=False)

    user_content: Mapped["UserContent"] = relationship("UserContent", back_populates="watched_episodes")
    episode: Mapped["Episode"] = relationship("Episode")

    def __repr__(self) -> str:
        return f"<WatchedEpisode uc={self.user_content_id} ep={self.episode_id}>"
