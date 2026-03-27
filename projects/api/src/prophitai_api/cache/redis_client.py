"""
Redis cache client for the ProphitAI API.

Provides async Redis operations with JSON serialization,
pattern-based clearing, and statistics monitoring.
"""

import os
import orjson
import logging
import asyncio
from redis.asyncio import Redis
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache client for FastAPI"""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.client: Optional[Redis] = None

    def _format_bytes(self, bytes_value: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f}PB"

    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_url:
            logger.warning("REDIS_URL not set - caching disabled")
            return

        try:
            self.client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=10,
                socket_timeout=30,
            )

            # Test connection
            await self.client.ping()
            logger.info("Redis connected successfully")

        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value:
                logger.info(f"Cache HIT: {key}")
                return orjson.loads(value)
            logger.info(f"Cache MISS: {key}")
            return None

        except Exception as e:
            logger.error(f"Redis GET error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.client:
            return False

        try:
            serialized = orjson.dumps(value, default=str).decode()
            await self.client.setex(key, ttl, serialized)
            logger.info(f"Cache SET: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Redis SET error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self.client:
            return False

        try:
            await self.client.delete(key)
            logger.info(f"Cache DELETE: {key}")
            return True

        except Exception as e:
            logger.error(f"Redis DELETE error for {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern

        Example: clear_pattern("economic:SPY:*")
        Returns: Number of keys deleted
        """
        if not self.client:
            return 0

        try:
            keys = await self.client.keys(pattern)
            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching: {pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Redis CLEAR error for {pattern}: {e}")
            return 0

    async def get_stats(self) -> dict:
        """
        Get Redis cache statistics for monitoring

        Returns metrics like:
        - Hit rate percentage
        - Memory usage
        - Connected clients
        - Total commands processed
        - Evicted keys
        """
        if not self.client:
            return {
                "status": "disconnected",
                "error": "Redis client not connected"
            }

        try:
            # Get Redis server info
            info = await self.client.info()

            # Calculate hit rate
            hits = int(info.get('keyspace_hits', 0))
            misses = int(info.get('keyspace_misses', 0))
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

            # Get keyspace info (number of keys per database)
            keyspace_info = {}
            for key, value in info.items():
                if key.startswith('db'):
                    keyspace_info[key] = value

            # Calculate memory remaining
            used_memory = int(info.get('used_memory', 0))
            max_memory = int(info.get('maxmemory', 0))

            if max_memory > 0:
                memory_remaining = max_memory - used_memory
                memory_remaining_human = self._format_bytes(memory_remaining)
                max_memory_human = self._format_bytes(max_memory)
                memory_percent_used = round((used_memory / max_memory) * 100, 2)
            else:
                memory_remaining_human = "unlimited"
                max_memory_human = "unlimited"
                memory_percent_used = 0

            return {
                "status": "connected",
                "redis_version": info.get('redis_version', 'unknown'),

                # Performance metrics
                "hit_rate_percent": round(hit_rate, 2),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "total_requests": total_requests,

                # Memory metrics
                "used_memory": info.get('used_memory_human', 'unknown'),
                "used_memory_peak": info.get('used_memory_peak_human', 'unknown'),
                "max_memory": max_memory_human,
                "memory_remaining": memory_remaining_human,
                "memory_percent_used": memory_percent_used,
                "memory_fragmentation_ratio": info.get('mem_fragmentation_ratio', 0),

                # Connection metrics
                "connected_clients": info.get('connected_clients', 0),
                "blocked_clients": info.get('blocked_clients', 0),

                # Key metrics
                "total_keys": sum(int(v.get('keys', 0)) for v in keyspace_info.values() if isinstance(v, dict)),
                "evicted_keys": info.get('evicted_keys', 0),
                "expired_keys": info.get('expired_keys', 0),

                # Server metrics
                "total_commands_processed": info.get('total_commands_processed', 0),
                "instantaneous_ops_per_sec": info.get('instantaneous_ops_per_sec', 0),
                "uptime_in_seconds": info.get('uptime_in_seconds', 0),
                "uptime_in_days": info.get('uptime_in_days', 0),

                # Database info
                "keyspace": keyspace_info
            }

        except Exception as e:
            logger.error(f"Redis STATS error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def start_stats_logger(self, interval_seconds: int = 120):
        """
        Background task that logs cache stats periodically

        Args:
            interval_seconds: How often to log stats (default: 120 = 2 minutes)
        """
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                stats = await self.get_stats()
                if stats.get("status") == "connected":
                    logger.info(
                        f"Cache Stats - Hit Rate: {stats['hit_rate_percent']}% | "
                        f"Total Keys: {stats['total_keys']} | "
                        f"Memory Used: {stats['used_memory']} / {stats['max_memory']} "
                        f"({stats['memory_percent_used']}%) | "
                        f"Remaining: {stats['memory_remaining']}"
                    )
                else:
                    logger.warning(f"Cache Stats - Status: {stats.get('status')}")
            except Exception as e:
                logger.error(f"Failed to retrieve cache stats: {e}")

# Global cache instance
cache = RedisCache()
