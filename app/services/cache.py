import time
from typing import Any


class TTLCache:
    """
    Minimalan in-memory cache sa TTL-om, dovoljan za jednog korisnika (V1).

    Ne treba nam Redis za personalnu aplikaciju - ovo štedi TMDB/TVmaze pozive
    kada se ista stranica (npr. Dashboard) osvežava u kratkom periodu.
    Ako aplikacija ikad postane multi-process (npr. gunicorn sa više workera),
    ovo treba zameniti spoljnim cache-om.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)

    def clear(self) -> None:
        self._store.clear()


# Jedan deljeni cache za ceo proces
cache = TTLCache()
