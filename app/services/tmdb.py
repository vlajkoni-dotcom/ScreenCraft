import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.services.cache import cache

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class TMDBError(Exception):
    """Podignuto kad TMDB API vrati grešku posle svih pokušaja - nikad ne izmišljamo podatke."""


class TMDBClient:
    """
    Async klijent za TMDB API v3.

    Pokriva i serije (tv) i filmove (movie) - endpoint prefiks se bira po
    'media_type' parametru gde god je to primenjivo, da izbegnemo duplirani
    kod za dve skoro identične familije endpointa.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.tmdb_base_url
        self.api_key = settings.tmdb_api_key
        self.language = settings.tmdb_language
        self.default_region = settings.default_region
        self.cache_ttl = settings.cache_ttl_seconds

        if not self.api_key:
            logger.warning(
                "TMDB_API_KEY nije podešen u .env - pozivi ka TMDB API-ju će odbijati."
            )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, TMDBError)),
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(params or {})
        params["api_key"] = self.api_key
        params.setdefault("language", self.language)

        cache_key = f"tmdb:{path}:{sorted(params.items())}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}{path}", params=params)

        if response.status_code in RETRYABLE_STATUS:
            raise TMDBError(f"TMDB {response.status_code} za {path}, pokušavam ponovo")
        if response.status_code == 401:
            raise TMDBError("TMDB API ključ je nevažeći ili nije podešen (401).")
        if response.status_code == 404:
            return {}
        response.raise_for_status()

        data = response.json()
        cache.set(cache_key, data, self.cache_ttl)
        return data

    # ---------- SERIJE ----------

    async def search_tv(self, query: str, year: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": query}
        if year:
            params["first_air_date_year"] = year
        data = await self._get("/search/tv", params)
        return data.get("results", [])

    async def get_tv_details(self, tmdb_id: int) -> dict[str, Any]:
        return await self._get(f"/tv/{tmdb_id}", {"append_to_response": "credits"})

    async def get_tv_season(self, tmdb_id: int, season_number: int) -> dict[str, Any]:
        return await self._get(f"/tv/{tmdb_id}/season/{season_number}")

    async def get_tv_watch_providers(self, tmdb_id: int) -> dict[str, Any]:
        """Vraća JustWatch-licencirane podatke o dostupnosti, po regionu (npr. 'RS')."""
        data = await self._get(f"/tv/{tmdb_id}/watch/providers")
        return data.get("results", {})

    async def get_tv_recommendations(self, tmdb_id: int) -> list[dict[str, Any]]:
        data = await self._get(f"/tv/{tmdb_id}/recommendations")
        return data.get("results", [])

    async def get_tv_similar(self, tmdb_id: int) -> list[dict[str, Any]]:
        data = await self._get(f"/tv/{tmdb_id}/similar")
        return data.get("results", [])

    async def discover_tv(self, **filters: Any) -> list[dict[str, Any]]:
        """filters npr: with_genres, with_watch_providers, watch_region, air_date.gte/lte"""
        data = await self._get("/discover/tv", filters)
        return data.get("results", [])

    async def get_tv_genre_list(self) -> list[dict[str, Any]]:
        data = await self._get("/genre/tv/list")
        return data.get("genres", [])

    async def get_tv_watch_provider_list(self, region: str) -> list[dict[str, Any]]:
        """Lista streaming platformi dostupnih u datom regionu - koristi se za filter na New Series stranici."""
        data = await self._get("/watch/providers/tv", {"watch_region": region})
        return data.get("results", [])

    # ---------- FILMOVI ----------

    async def search_movie(self, query: str, year: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": query}
        if year:
            params["year"] = year
        data = await self._get("/search/movie", params)
        return data.get("results", [])

    async def get_movie_details(self, tmdb_id: int) -> dict[str, Any]:
        return await self._get(f"/movie/{tmdb_id}", {"append_to_response": "credits"})

    async def get_movie_watch_providers(self, tmdb_id: int) -> dict[str, Any]:
        data = await self._get(f"/movie/{tmdb_id}/watch/providers")
        return data.get("results", {})

    async def get_movie_recommendations(self, tmdb_id: int) -> list[dict[str, Any]]:
        data = await self._get(f"/movie/{tmdb_id}/recommendations")
        return data.get("results", [])

    async def discover_movie(self, **filters: Any) -> list[dict[str, Any]]:
        data = await self._get("/discover/movie", filters)
        return data.get("results", [])

    async def get_movie_genre_list(self) -> list[dict[str, Any]]:
        data = await self._get("/genre/movie/list")
        return data.get("genres", [])

    async def get_movie_release_dates(self, tmdb_id: int) -> list[dict[str, Any]]:
        """Vraća release_dates po zemlji - koristimo da nadjemo STVARAN (ne najavljen) digital/BD datum."""
        data = await self._get(f"/movie/{tmdb_id}/release_dates")
        return data.get("results", [])

    # ---------- MULTI ----------

    async def search_multi(self, query: str) -> list[dict[str, Any]]:
        """Pretraga i serija i filmova odjednom - koristi se na SEARCH stranici."""
        data = await self._get("/search/multi", {"query": query})
        results = data.get("results", [])
        return [r for r in results if r.get("media_type") in ("tv", "movie")]


tmdb_client = TMDBClient()
