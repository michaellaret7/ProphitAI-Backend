from fastapi import APIRouter, Query
from typing import Dict, Any
from prophitai_api.cache.redis_client import cache

router = APIRouter(tags=["Cache Management 💾"])


@router.delete("/cache/clear")
async def clear_cache(pattern: str = Query("*", description="Pattern to match cache keys (e.g., 'alts:*', 'portfolio:*')")):
    """
    Clear cache keys matching a pattern

    Examples:
    - Clear all alts: /api/cache/clear?pattern=alts:*
    - Clear specific portfolio: /api/cache/clear?pattern=portfolio:*:abc-123:*
    - Clear everything: /api/cache/clear?pattern=*
    """
    deleted_count = await cache.clear_pattern(pattern)

    return {
        "message": f"Cache cleared successfully",
        "pattern": pattern,
        "keys_deleted": deleted_count
    }


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get Redis cache statistics

    Returns hit rate, memory usage, key counts, etc.
    """
    stats = await cache.get_stats()
    return {
        "message": "Cache statistics retrieved successfully",
        "stats": stats
    }
