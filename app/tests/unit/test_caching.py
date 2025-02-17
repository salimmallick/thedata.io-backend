import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import patch, Mock
from app.api.core.cache import CacheManager
from app.api.core.redis import redis
from app.api.core.config import settings

# Override Redis URL for tests
settings.REDIS_URL = "redis://redis-test:6379/0"

@pytest.fixture
async def redis_connection():
    """Fixture to provide Redis connection"""
    try:
        await redis.connect()
        await redis.delete("test:*")  # Clean up any existing test keys
        yield redis
    finally:
        await redis.delete("test:*")  # Clean up after tests
        await redis.disconnect()

@pytest.fixture
async def cache(redis_connection):
    """Fixture to provide cache manager instance"""
    cache_instance = CacheManager()
    yield cache_instance

@pytest.mark.asyncio
async def test_cache_initialization(cache):
    """Test cache manager initialization"""
    cache_instance = await anext(cache)
    assert cache_instance._default_ttl == 300  # 5 minutes
    assert isinstance(cache_instance.patterns, dict)
    assert cache_instance.max_memory_usage == 512 * 1024 * 1024  # 512MB

@pytest.mark.asyncio
async def test_cache_set_get(cache, redis_connection):
    """Test basic cache set and get operations"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    test_key = "test_key_1"
    test_value = {"data": "test_value", "timestamp": datetime.utcnow().isoformat()}
    
    # Set value in cache
    await cache_instance.set(test_key, test_value)
    
    # Get value from cache
    cached_value = await cache_instance.get(test_key)
    assert cached_value == test_value

@pytest.mark.asyncio
async def test_cache_ttl(cache, redis_connection):
    """Test cache TTL functionality"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    test_key = "test_key_2"
    test_value = {"data": "test_value"}
    test_ttl = 2  # 2 seconds TTL

    # Set value with TTL
    await cache_instance.set(test_key, test_value, ttl=test_ttl)
    
    # Verify value exists
    cached_value = await cache_instance.get(test_key)
    assert cached_value == test_value
    
    # Wait for TTL to expire
    await asyncio.sleep(test_ttl + 1)
    
    # Verify value is gone
    expired_value = await cache_instance.get(test_key)
    assert expired_value is None

@pytest.mark.asyncio
async def test_cache_delete(cache, redis_connection):
    """Test cache deletion"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    test_key = "test_key_3"
    test_value = {"data": "test_value"}

    # Set value
    await cache_instance.set(test_key, test_value)
    
    # Verify value exists
    assert await cache_instance.get(test_key) == test_value
    
    # Delete value
    await cache_instance.delete(test_key)
    
    # Verify value is gone
    assert await cache_instance.get(test_key) is None

@pytest.mark.asyncio
async def test_cache_pattern_invalidation(cache, redis_connection):
    """Test cache invalidation by pattern"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    # Set multiple values with patterns
    test_data = {
        "user:1": {"data": "user1_data"},
        "user:2": {"data": "user2_data"},
        "post:1": {"data": "post1_data"}
    }

    for key, value in test_data.items():
        await cache_instance.set(
            key,
            value,
            patterns=["user:*"] if key.startswith("user") else ["post:*"]
        )

    # Verify all values exist
    for key, value in test_data.items():
        assert await cache_instance.get(key) == value

    # Invalidate user pattern
    await cache_instance.invalidate_pattern("user:*")

    # Verify user values are gone but post remains
    assert await cache_instance.get("user:1") is None
    assert await cache_instance.get("user:2") is None
    assert await cache_instance.get("post:1") == test_data["post:1"]

@pytest.mark.asyncio
async def test_cache_stats(cache, redis_connection):
    """Test cache statistics"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    # Add some test data
    test_data = {
        "test_key_4": {"data": "value1"},
        "test_key_5": {"data": "value2"}
    }

    for key, value in test_data.items():
        await cache_instance.set(key, value)

    # Get stats
    stats = await cache_instance.get_stats()
    assert isinstance(stats, dict)
    assert stats["hits"] >= 0
    assert stats["misses"] >= 0
    assert stats["memory_usage"] >= 0

@pytest.mark.asyncio
async def test_cache_cleanup_expired(cache, redis_connection):
    """Test cleanup of expired cache entries"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    # Add test data with short TTL
    test_data = {
        "expire_key_1": {"data": "value1"},
        "expire_key_2": {"data": "value2"}
    }

    for key, value in test_data.items():
        await cache_instance.set(key, value, ttl=1)

    # Wait for TTL to expire
    await asyncio.sleep(2)

    # Run cleanup
    await cache_instance.cleanup_expired()

    # Verify all values are gone
    for key in test_data:
        assert await cache_instance.get(key) is None

@pytest.mark.asyncio
async def test_cache_warm_up(cache, redis_connection):
    """Test cache warm-up functionality"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    async def test_query():
        return {"data": "warm_up_data"}

    # Register warm-up query
    await cache_instance.register_warm_up_query("warm_up_key", test_query)

    # Execute warm-up
    await cache_instance.warm_up()

    # Verify data is cached
    cached_value = await cache_instance.get("warm_up_key")
    assert cached_value == {"data": "warm_up_data"}

@pytest.mark.asyncio
async def test_cache_eviction(cache, redis_connection):
    """Test cache eviction"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    # Fill cache with test data
    for i in range(10):
        await cache_instance.set(
            f"evict_key_{i}",
            {"data": f"value_{i}", "size": 1024 * 1024}  # 1MB each
        )

    # Add one more entry to trigger eviction
    await cache_instance.set(
        "evict_trigger",
        {"data": "trigger", "size": 1024 * 1024}
    )

    # Explicitly trigger eviction
    await cache_instance.evict_entries(target_memory_usage=0)

    # Verify some old entries were evicted
    evicted = False
    for i in range(10):
        if await cache_instance.get(f"evict_key_{i}") is None:
            evicted = True
            break
    assert evicted

@pytest.mark.asyncio
async def test_cache_redis_failure(cache, redis_connection):
    """Test cache behavior when Redis fails"""
    cache_instance = await anext(cache)
    redis_conn = await anext(redis_connection)
    test_key = "test_key_6"
    test_value = {"data": "test_value"}

    # Mock Redis failure using unittest.mock
    with patch.object(redis_conn, 'set', side_effect=Exception("Redis connection failed")):
        # Should handle Redis failure gracefully
        try:
            await cache_instance.set(test_key, test_value)
        except Exception:
            pytest.fail("Cache should handle Redis failure gracefully") 