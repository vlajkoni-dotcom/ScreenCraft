import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.services.cache import cache

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class TVmazeError(Exception):
    """Podignuto kad TVmaze API vrati grešku posle svih pokušaja."""


class TVmazeClient:
    """
    Async klijent za TVmaze API - javno dostupan, bez API ključa.

    Koristi se ISKLJUČIVO za serije (filmovi nisu deo TVmaze-a) i to
    prvenstveno za schedule podatke (air_date/air_time) - TVmaze je primarni
    izvor za schedule po dogovorenom pravilu (TMDB je primaran za metadata).

    Rate limit je oko 20 poziva / 10 sekundi po IP adresi - cache i retry sa
    exponential backoff-om su zato obavezni, ne opcioni.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.tvmaze_base_url
        self.cache_ttl = settings.cache_ttl_seconds

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, TVmazeError)),
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        cache_key = f"tvmaze:{path}:{sorted((params or {}).items())}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}{path}", params=params)

        if response.status_code == 429 or response.status_code in RETRYABLE_STATUS:
            raise TVmazeError(f"TVmaze {response.status_code} za {path}, pokušavam ponovo")
        if response.status_code == 404:
            return None
        response.raise_for_status()

        data = response.json()
        cache.set(cache_key, data, self.cache_ttl)
        return data

    async def search_shows(self, query: str) -> list[dict[str, Any]]:
        data = await self._get("/search/shows", {"q": query})
        return data or []

    async def get_show(self, tvmaze_id: int) -> dict[str, Any] | None:
        return await self._get(f"/shows/{tvmaze_id}")

    async def get_show_episodes(self, tvmaze_id: int) -> list[dict[str, Any]]:
        """Vraća SVE epizode (prošle i najavljene) - koristi se za sync rasporeda."""
        data = await self._get(f"/shows/{tvmaze_id}/episodes", {"specials": "0"})
        return data or []

    async def get_show_by_tmdb_id_lookup(self, imdb_id: str) -> dict[str, Any] | None:
        """TVmaze podržava lookup preko IMDB ID-a - korisno kad imamo TMDB match ali ne i TVmaze."""
        return await self._get("/lookup/shows", {"imdb": imdb_id})


tvmaze_client = TVmazeClient()
