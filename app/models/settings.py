from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class AppSetting(Base):
    """Prosta key-value tabela za podešavanja (npr. region, timezone).
    Za V1 (single user) dovoljno - ako ikad budemo imali više korisnika,
    ovde dodajemo user_id."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
