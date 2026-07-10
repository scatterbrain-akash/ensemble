from __future__ import annotations

import time
from typing import Any


class CacheService:
    def __init__(self) -> None:
        self.store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self.store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            del self.store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.store[key] = (time.time() + ttl_seconds, value)
