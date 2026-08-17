import enum

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.content_common import ContentType, TimestampMixin


class OfferType(str, enum.Enum):
    FLATRATE = "flatrate"  # uključeno u pretplatu
    RENT = "rent"
    BUY = "buy"
    FREE = "free"
    ADS = "ads"


class Provider(Base):
    """Streaming platforma, npr. Netflix, HBO Max, Prime Video."""

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_provider_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Provider {self.name}>"


class Availability(Base, TimestampMixin):
    """
    Gde je serija/film dostupan za gledanje, po zemlji.

    content_type + content_id upućuju na shows.id ili movies.id (polimorfna
    veza bez FK-a, pošto povezujemo dve različite tabele istim mehanizmom;
    integritet se čuva na nivou servisa, ne baze).
    """

    __tablename__ = "availability"
    __table_args__ = (
        UniqueConstraint(
            "content_type", "content_id", "provider_id", "country_code", "offer_type",
            name="uq_availability_unique_offer",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    offer_type: Mapped[str] = mapped_column(String(16), nullable=False)

    # Odakle je podatak došao - trenutno uvek "tmdb" (JustWatch-licencirani podaci
    # preko TMDB /watch/providers endpointa), pripremljeno za budući "justwatch_partner"
    source: Mapped[str] = mapped_column(String(32), default="tmdb", nullable=False)

    provider: Mapped["Provider"] = relationship("Provider")

    def __repr__(self) -> str:
        return f"<Availability {self.content_type}:{self.content_id} @ {self.provider_id} ({self.country_code})>"
