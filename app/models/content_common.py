import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class ContentType(str, enum.Enum):
    """Da li se stavka odnosi na seriju ili film - koristi se u user_content."""

    SHOW = "show"
    MOVIE = "movie"


class UserContentStatus(str, enum.Enum):
    """
    Status koji korisnik dodeljuje seriji ili filmu.

    Tok:
        WATCHING -> WATCHED
        WATCHING -> DROPPED / PAUSED
        (bilo koje) -> WATCHLIST
        NEW/preporuka -> NOT_INTERESTED  (eksplicitno odbijeno, negativan signal
                                           za recommendation engine; razlikuje se
                                           od "nikad viđeno" tj. odsustva statusa)
    """

    WATCHING = "watching"
    WATCHLIST = "watchlist"
    WATCHED = "watched"
    DROPPED = "dropped"
    PAUSED = "paused"
    NOT_INTERESTED = "not_interested"


class ShowAiringStatus(str, enum.Enum):
    """TMDB 'status' polje za serije - bitno za logiku 'sledeća epizoda'."""

    RETURNING_SERIES = "Returning Series"
    ENDED = "Ended"
    CANCELED = "Canceled"
    IN_PRODUCTION = "In Production"
    PLANNED = "Planned"
    PILOT = "Pilot"
    UNKNOWN = "Unknown"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin koji dodaje created_at / updated_at svakom modelu koji ga nasledi."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
