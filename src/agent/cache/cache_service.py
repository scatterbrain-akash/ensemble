from __future__ import annotations

import time
from typing import Any


class CacheService:
    """Simple cache service with optional Redis backend.

    If `settings.cache.backend` == 'redis' and `redis` package is available,
    the cache will use Redis. Otherwise it falls back to an in-memory TTL store.
    """

    def __init__(self, settings: object | None = None) -> None:
        self._use_redis = False
        self._redis = None
        self.store: dict[str, tuple[float, Any]] = {}
        self.settings = settings or {}
        backend = None
        try:
            backend = getattr(settings, "cache", {}).get("backend") if settings is not None else None
        except Exception:
            backend = None

        if backend == "redis":
            try:
                import redis

                redis_url = getattr(settings, "cache", {}).get("redis_url", "redis://localhost:6379/0")
                self._redis = redis.from_url(redis_url)
                # quick health check
                self._redis.ping()
                self._use_redis = True
            except Exception:
                # fall back to in-memory if redis not available
                self._use_redis = False
        # if redis not configured, optionally use a file-backed store
        if not self._use_redis:
            file_path = getattr(settings, "cache", {}).get("file_path") if settings is not None else None
            if file_path:
                try:
                    from pathlib import Path
                    import json

                    self._file_path = Path(file_path)
                    self._file_path.parent.mkdir(parents=True, exist_ok=True)
                    if self._file_path.exists():
                        raw = self._file_path.read_text(encoding="utf-8")
                        try:
                            data = json.loads(raw)
                        except Exception:
                            data = {}
                        # load into in-memory store with expiry
                        now = time.time()
                        for k, v in data.items():
                            expires_at = v.get("expires_at", 0)
                            value = v.get("value")
                            if expires_at > now:
                                self.store[k] = (expires_at, value)
                except Exception:
                    self._file_path = None
            else:
                self._file_path = None

    def get(self, key: str) -> Any | None:
        if self._use_redis and self._redis:
            try:
                val = self._redis.get(key)
                if val is None:
                    return None
                try:
                    import json

                    return json.loads(val)
                except Exception:
                    return val
            except Exception:
                return None

        item = self.store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            del self.store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if self._use_redis and self._redis:
            try:
                import json

                self._redis.setex(key, int(ttl_seconds), json.dumps(value))
                return
            except Exception:
                pass

        expires = time.time() + ttl_seconds
        self.store[key] = (expires, value)

        # persist to file if configured
        if getattr(self, "_file_path", None) is not None:
            try:
                import json

                # read current file, update key, write atomically
                data = {}
                if self._file_path.exists():
                    raw = self._file_path.read_text(encoding="utf-8")
                    try:
                        data = json.loads(raw)
                    except Exception:
                        data = {}
                data[key] = {"expires_at": expires, "value": value}
                tmp = self._file_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(data), encoding="utf-8")
                tmp.replace(self._file_path)
            except Exception:
                pass
