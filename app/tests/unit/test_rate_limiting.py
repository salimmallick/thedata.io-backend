import pytest
from datetime import datetime
import time
from app.api.core.rate_limit import RateLimiter, RateLimitExceededError
from app.api.core.redis import redis

@pytest.fixture
async def rate_limiter():
    """Create a test rate limiter instance"""
    limiter = RateLimiter(
        key_prefix="test_limiter",
        max_requests=5,
        time_window=60
    )
    yield limiter

@pytest.fixture
async def redis_connection():
    """Ensure Redis connection for tests"""
    await redis.connect()
    yield redis
    await redis.disconnect()

@pytest.mark.asyncio
async def test_rate_limiter_initialization(rate_limiter):
    """Test rate limiter initialization"""
    assert rate_limiter.key_prefix == "test_limiter"
    assert rate_limiter.max_requests == 5
    assert rate_limiter.time_window == 60

@pytest.mark.asyncio
async def test_rate_limiter_check_under_limit(rate_limiter, redis_connection):
    """Test rate limiting when under the limit"""
    identifier = "test_user_1"
    
    # Make requests under the limit
    for _ in range(5):
        allowed = await rate_limiter.check_rate_limit(identifier)
        assert allowed is True

@pytest.mark.asyncio
async def test_rate_limiter_check_exceed_limit(rate_limiter, redis_connection):
    """Test rate limiting when exceeding the limit"""
    identifier = "test_user_2"
    
    # Make requests up to the limit
    for _ in range(5):
        allowed = await rate_limiter.check_rate_limit(identifier)
        assert allowed is True
    
    # Next request should be denied
    allowed = await rate_limiter.check_rate_limit(identifier)
    assert allowed is False

@pytest.mark.asyncio
async def test_rate_limiter_window_reset(rate_limiter, redis_connection):
    """Test rate limit window reset"""
    identifier = "test_user_3"
    test_window = 2  # 2 second window for testing
    
    # Create a new limiter with shorter window
    test_limiter = RateLimiter(
        key_prefix="test_short_window",
        max_requests=2,
        time_window=test_window
    )
    
    # Use up the limit
    for _ in range(2):
        allowed = await test_limiter.check_rate_limit(identifier)
        assert allowed is True
    
    # Wait for window to reset
    await asyncio.sleep(test_window + 1)
    
    # Should be allowed again
    allowed = await test_limiter.check_rate_limit(identifier)
    assert allowed is True

@pytest.mark.asyncio
async def test_rate_limiter_multiple_identifiers(rate_limiter, redis_connection):
    """Test rate limiting for different identifiers"""
    identifier1 = "test_user_4"
    identifier2 = "test_user_5"
    
    # Use up limit for first identifier
    for _ in range(5):
        allowed = await rate_limiter.check_rate_limit(identifier1)
        assert allowed is True
    
    # First identifier should be blocked
    allowed = await rate_limiter.check_rate_limit(identifier1)
    assert allowed is False
    
    # Second identifier should still be allowed
    for _ in range(5):
        allowed = await rate_limiter.check_rate_limit(identifier2)
        assert allowed is True

@pytest.mark.asyncio
async def test_rate_limiter_redis_failure(rate_limiter, redis_connection, mocker):
    """Test rate limiter behavior when Redis fails"""
    identifier = "test_user_6"
    
    # Mock Redis failure
    mocker.patch.object(
        rate_limiter,
        '_get_redis',
        side_effect=Exception("Redis connection failed")
    )
    
    # Should fail closed (deny request) on Redis failure
    allowed = await rate_limiter.check_rate_limit(identifier)
    assert allowed is False

@pytest.mark.asyncio
async def test_get_remaining_requests(rate_limiter, redis_connection):
    """Test getting remaining request count"""
    identifier = "test_user_7"
    
    # Initial remaining should be max_requests
    remaining = await rate_limiter.get_remaining_requests(identifier)
    assert remaining == rate_limiter.max_requests
    
    # Use some requests
    for _ in range(3):
        await rate_limiter.check_rate_limit(identifier)
    
    # Check remaining
    remaining = await rate_limiter.get_remaining_requests(identifier)
    assert remaining == 2

@pytest.mark.asyncio
async def test_rate_limiter_reset(rate_limiter, redis_connection):
    """Test resetting rate limit for an identifier"""
    identifier = "test_user_8"
    
    # Use up some requests
    for _ in range(3):
        await rate_limiter.check_rate_limit(identifier)
    
    # Reset the limit
    success = await rate_limiter.reset_limit(identifier)
    assert success is True
    
    # Should have full limit available again
    remaining = await rate_limiter.get_remaining_requests(identifier)
    assert remaining == rate_limiter.max_requests 