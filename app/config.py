from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralna konfiguracija aplikacije, učitava se iz .env fajla."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tmdb_api_key: str = ""
    default_region: str = "RS"
    default_timezone: str = "Europe/Belgrade"
    database_url: str = "sqlite+aiosqlite:///./data/tracker.db"
    log_level: str = "INFO"
    cache_ttl_seconds: int = 3600

    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tvmaze_base_url: str = "https://api.tvmaze.com"

    # ISO-639-1 jezik za TMDB odgovore (metadata, opisi)
    tmdb_language: str = "en-US"


@lru_cache
def get_settings() -> Settings:
    return Settings()
