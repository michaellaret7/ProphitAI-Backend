"""Synchronous Redis client for use in non-async code paths (agent tools, calc engine)."""

import os
import logging
import threading
from typing import Any, Optional

import orjson
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SyncRedisCache:
    """Sync Redis cache for synchronous code paths.

    Uses the same REDIS_URL as the async client. All methods are
    fail-safe — returns None/False when Redis is unavailable so
    callers always have a working fallback path.

    Connection is lazy — established on first get/set call, not at import time.
    Thread-safe via double-checked locking on connection init.
    """

    def __init__(self) -> None:
        self.redis_url = os.getenv("REDIS_URL")
        self.client: Optional[Redis] = None
        self._attempted: bool = False
        self._conn_lock = threading.Lock()

    def _ensure_connected(self) -> None:
        """Lazily establish Redis connection on first use."""
        if self._attempted:
            return

        with self._conn_lock:
            # Reason: double-check after acquiring lock to avoid redundant connections
            if self._attempted:
                return

            if not self.redis_url:
                self._attempted = True
                logger.warning("REDIS_URL not set — sync cache disabled")
                return

            try:
                self.client = Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    encoding="utf-8",
                    socket_connect_timeout=5,
                    socket_timeout=10,
                )
                self.client.ping()
                logger.info("Sync Redis connected")
            except Exception as e:
                logger.warning("Sync Redis connection failed: %s", e)
                self.client = None
            finally:
                self._attempted = True

    def get(self, key: str) -> Optional[Any]:
        """Get and deserialize a value from Redis."""
        self._ensure_connected()
        if not self.client:
            return None
        try:
            value: str | None = self.client.get(key)  # type: ignore[assignment]
            if value is not None:
                return orjson.loads(value)
            return None
        except Exception as e:
            logger.warning("Sync Redis GET error for %s: %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Serialize and store a value in Redis with TTL (seconds)."""
        self._ensure_connected()
        if not self.client:
            return False
        try:
            serialized = orjson.dumps(value, default=str).decode()
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning("Sync Redis SET error for %s: %s", key, e)
            return False


# ================================
# --> Module-level singleton
# ================================

sync_cache = SyncRedisCache()
