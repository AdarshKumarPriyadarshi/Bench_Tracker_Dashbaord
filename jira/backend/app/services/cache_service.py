import time
from typing import Any

from app.config import settings


class CacheService:
    def __init__(self, ttl: int | None = None):
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl or settings.cache_ttl_seconds

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.time() + (ttl or self._ttl)
        self._store[key] = (value, expires_at)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]

    def clear(self) -> None:
        self._store.clear()


cache = CacheService()
