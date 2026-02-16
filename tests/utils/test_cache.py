import time

from utils.cache import TTLCache, ttl_cache


class TestTTLCache:
    """Test TTL cache implementation"""

    def test_cache_stores_and_retrieves_value(self):
        """Test that cache stores and retrieves values"""
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_returns_none_for_missing_key(self):
        """Test that cache returns None for missing keys"""
        cache = TTLCache(ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_cache_expires_after_ttl(self):
        """Test that cache values expire after TTL"""
        cache = TTLCache(ttl_seconds=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """Test that clear removes all cached values"""
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestTTLCacheDecorator:
    """Test TTL cache decorator"""

    def test_decorator_caches_function_result(self):
        """Test that decorator caches function results"""
        call_count = [0]

        @ttl_cache(ttl_seconds=60)
        def expensive_function(x: int) -> int:
            call_count[0] += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count[0] == 1

    def test_decorator_respects_different_arguments(self):
        """Test that decorator caches different arguments separately"""
        call_count = [0]

        @ttl_cache(ttl_seconds=60)
        def add(x: int, y: int) -> int:
            call_count[0] += 1
            return x + y

        result1 = add(1, 2)
        result2 = add(1, 2)
        result3 = add(2, 3)

        assert result1 == 3
        assert result2 == 3
        assert result3 == 5
        assert call_count[0] == 2

    def test_decorator_expires_after_ttl(self):
        """Test that decorator cache expires after TTL"""
        call_count = [0]

        @ttl_cache(ttl_seconds=1)
        def get_value() -> str:
            call_count[0] += 1
            return "test"

        result1 = get_value()
        time.sleep(1.1)
        result2 = get_value()

        assert result1 == "test"
        assert result2 == "test"
        assert call_count[0] == 2

    def test_decorator_cache_clear(self):
        """Test that cache_clear clears the cache"""
        call_count = [0]

        @ttl_cache(ttl_seconds=60)
        def get_value() -> str:
            call_count[0] += 1
            return "test"

        result1 = get_value()
        get_value.cache_clear()
        result2 = get_value()

        assert result1 == "test"
        assert result2 == "test"
        assert call_count[0] == 2
