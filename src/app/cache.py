from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Minimal in-memory TTL cache.

    Not thread-safe on its own but safe enough for a single asyncio loop:
    all mutations happen synchronously (no awaits between read and write).
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: T) -> None:
        self._data[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)
