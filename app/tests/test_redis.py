import pytest
from httpx import AsyncClient
import time
import json
from ..api.core.redis import redis
from ..api.models.organization import Organization

@pytest.fixture
async def setup_redis():
    """Setup Redis for testing"""
    await redis.connect()
    yield redis
    # Clear test data
    await redis._redis.flushdb()
    await redis.disconnect()

@pytest.mark.asyncio
async def test_redis_caching(setup_redis):
    """Test Redis caching functionality"""
    test_key = "test:cache:key"
    test_data = {"message": "Hello, World!"}
    
    # Set cache
    await redis.set_cache(test_key, test_data, expire_seconds=1)
    
    # Get from cache
    cached_data = await redis.get_cache(test_key)
    assert cached_data == test_data
    
    # Wait for expiration
    await asyncio.sleep(1.1)
    
    # Should be None after expiration
    expired_data = await redis.get_cache(test_key)
    assert expired_data is None

@pytest.mark.asyncio
async def test_rate_limiting(setup_redis):
    """Test Redis rate limiting functionality"""
    test_key = "test:ratelimit:key"
    limit = 5
    window = 1  # 1 second window
    
    # Should allow up to limit
    for _ in range(limit):
        assert await redis.check_rate_limit(test_key, limit, window)
    
    # Should deny after limit
    assert not await redis.check_rate_limit(test_key, limit, window)
    
    # Get rate limit info
    info = await redis.get_rate_limit_info(test_key, window)
    assert info["count"] == limit + 1
    assert 0 <= info["ttl"] <= window

@pytest.mark.asyncio
async def test_cached_endpoint(client: AsyncClient):
    """Test endpoint caching"""
    # First request - should hit the endpoint
    response1 = await client.get("/health")
    assert response1.status_code == 200
    assert "X-Cache-Hit" not in response1.headers
    
    # Second request - should be cached
    response2 = await client.get("/health")
    assert response2.status_code == 200
    assert response2.headers.get("X-Cache-Hit") == "true"
    assert response1.json() == response2.json()

@pytest.mark.asyncio
async def test_rate_limited_endpoint(
    client: AsyncClient,
    test_org: Organization,
    setup_redis
):
    """Test rate limited endpoint"""
    # Setup request
    timestamp = str(int(time.time()))
    path = "/ingest/events"
    method = "POST"
    body = json.dumps([{"event_type": "test"}])
    
    headers = {
        "X-API-Key": test_org.api_key,
        "X-Timestamp": timestamp,
        "X-Signature": generate_signature(
            test_org.api_secret,
            timestamp,
            method,
            path,
            body
        )
    }
    
    # Make requests up to the limit
    limit = 5  # Use small limit for testing
    for i in range(limit):
        response = await client.post(path, content=body, headers=headers)
        assert response.status_code == 200
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining == limit - (i + 1)
    
    # Next request should be rate limited
    response = await client.post(path, content=body, headers=headers)
    assert response.status_code == 429
    assert "Retry-After" in response.headers

@pytest.mark.asyncio
async def test_cache_invalidation(setup_redis):
    """Test cache invalidation"""
    test_key = "test:cache:invalidate"
    test_data = {"message": "Hello, World!"}
    
    # Set cache
    await redis.set_cache(test_key, test_data)
    
    # Verify cache exists
    assert await redis.get_cache(test_key) == test_data
    
    # Invalidate cache
    await redis.invalidate_cache(test_key)
    
    # Should be None after invalidation
    assert await redis.get_cache(test_key) is None

@pytest.mark.asyncio
async def test_redis_connection_handling(setup_redis):
    """Test Redis connection handling"""
    # Test automatic connection
    await redis.disconnect()
    assert not redis._connected
    
    # Should auto-connect when needed
    test_data = {"message": "Hello, World!"}
    await redis.set_cache("test:key", test_data)
    assert redis._connected
    
    # Test reconnection after disconnection
    await redis.disconnect()
    assert not redis._connected
    
    cached_data = await redis.get_cache("test:key")
    assert cached_data == test_data
    assert redis._connected 