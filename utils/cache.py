import time
from functools import wraps
from typing import Any, Callable, Dict, Optional


class TTLCache:
    """Simple TTL (Time To Live) cache implementation."""

    def __init__(self, ttl_seconds: int):
        """
        Initialize TTL cache.

        Args:
            ttl_seconds: Time to live in seconds for cached values
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired or not found
        """
        if key not in self._cache:
            return None

        cache_entry = self._cache[key]
        if time.time() - cache_entry["timestamp"] > self._ttl:
            del self._cache[key]
            return None

        return cache_entry["value"]

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = {"value": value, "timestamp": time.time()}

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


def ttl_cache(ttl_seconds: int) -> Callable:
    """
    Decorator to cache function results with TTL.

    Args:
        ttl_seconds: Time to live in seconds

    Returns:
        Decorator function
    """
    cache = TTLCache(ttl_seconds)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_key = f"{func.__name__}:{args}:{kwargs}"

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
