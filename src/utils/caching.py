"""
Caching utilities for expensive operations.
"""
import functools
import time

# Simple in-memory cache
_CACHE = {}
_CACHE_EXPIRY = {}
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)

def cache_result(func):
    """
    Decorator to cache function results to avoid redundant expensive operations.
    
    Usage:
        @cache_result
        def expensive_function(param1, param2):
            # Function code here
    
    Args:
        func: The function to cache
        
    Returns:
        Wrapped function that caches results
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create a unique key based on function name and arguments
        key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        
        # Check if result is in cache and not expired
        current_time = time.time()
        if key in _CACHE and _CACHE_EXPIRY.get(key, 0) > current_time:
            print(f"Cache hit for {func.__name__}")
            return _CACHE[key]
        
        # Execute function and cache result
        result = func(*args, **kwargs)
        _CACHE[key] = result
        _CACHE_EXPIRY[key] = current_time + CACHE_TTL
        return result
    
    return wrapper

def clear_cache():
    """
    Clear the entire cache.
    """
    global _CACHE, _CACHE_EXPIRY
    _CACHE = {}
    _CACHE_EXPIRY = {}
    print("Cache cleared")

def set_cache_ttl(seconds):
    """
    Set the cache time-to-live.
    
    Args:
        seconds: Number of seconds before cache entries expire
    """
    global CACHE_TTL
    CACHE_TTL = seconds
    print(f"Cache TTL set to {seconds} seconds") 