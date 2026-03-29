"""
Synchronous Redis cache client.

Used by calculation modules (e.g. factor_exposures) that run in
synchronous contexts and need Redis caching without async/await.
"""
import os
import orjson
import logging
from redis import Redis
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SyncRedisCache:
    """Synchronous Redis cache client with JSON serialization."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.client: Optional[Redis] = None
        self._connect()

    def _connect(self):
        """Initialize Redis connection."""
        if not self.redis_url:
            logger.warning("REDIS_URL not set - sync caching disabled")
            return

        try:
            self.client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=10,
                socket_timeout=30,
            )
            self.client.ping()
            logger.info("Sync Redis connected successfully")
        except Exception as e:
            logger.error(f"Sync Redis connection failed: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """Get and deserialize a value from cache."""
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                return orjson.loads(value)
            return None
        except Exception as e:
            logger.error(f"Sync Redis GET error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Serialize and set a value in cache with TTL."""
        if not self.client:
            return False

        try:
            serialized = orjson.dumps(value, default=str).decode()
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Sync Redis SET error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.client:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Sync Redis DELETE error for {key}: {e}")
            return False


sync_cache = SyncRedisCache()
