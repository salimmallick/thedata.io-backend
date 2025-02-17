import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.api.core.middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    CacheMiddleware,
    MonitoringMiddleware
)
from app.api.core.cache import cache_manager
from app.api.core.metrics import metrics
from app.api.core.config import settings

@pytest.fixture
def app():
    """Create a test FastAPI application"""
    app = FastAPI()
    return app

@pytest.fixture
def test_client(app):
    """Create a test client"""
    return TestClient(app)

@pytest.mark.asyncio
async def test_security_headers_middleware(app, test_client):
    """Test security headers middleware"""
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    response = test_client.get("/test")
    
    # Verify security headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers

@pytest.mark.asyncio
async def test_rate_limit_middleware(app, test_client):
    """Test rate limiting middleware"""
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    # Test successful requests
    for _ in range(settings.tier_limits["free"]):
        response = test_client.get("/test")
        assert response.status_code == 200
    
    # Test rate limit exceeded
    response = test_client.get("/test")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

@pytest.mark.asyncio
async def test_cache_middleware(app, test_client):
    """Test cache middleware"""
    app.add_middleware(CacheMiddleware)
    
    test_data = {"message": "test"}
    
    @app.get("/test")
    async def test_endpoint():
        return test_data
    
    # First request - should miss cache
    response1 = test_client.get("/test")
    assert response1.status_code == 200
    assert response1.json() == test_data
    
    # Second request - should hit cache
    response2 = test_client.get("/test")
    assert response2.status_code == 200
    assert response2.json() == test_data
    
    # Verify cache was used
    cache_key = f"cache:GET:/test:"
    cached_data = await cache_manager.get(cache_key)
    assert cached_data is not None

@pytest.mark.asyncio
async def test_monitoring_middleware(app, test_client):
    """Test monitoring middleware"""
    app.add_middleware(MonitoringMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    # Make test request
    response = test_client.get("/test")
    assert response.status_code == 200
    
    # Verify metrics were collected
    metric_value = metrics.http_requests_total.labels(
        method="GET",
        endpoint="/test",
        status=200
    )._value.get()
    assert metric_value == 1

@pytest.mark.asyncio
async def test_middleware_error_handling(app, test_client):
    """Test middleware error handling"""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CacheMiddleware)
    app.add_middleware(MonitoringMiddleware)
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    response = test_client.get("/error")
    assert response.status_code == 500
    
    # Verify error metrics were collected
    metric_value = metrics.http_requests_total.labels(
        method="GET",
        endpoint="/error",
        status=500
    )._value.get()
    assert metric_value == 1

@pytest.mark.asyncio
async def test_middleware_async_compatibility(app):
    """Test middleware async compatibility"""
    middleware = SecurityHeadersMiddleware(app)
    
    # Create mock request and response
    mock_request = Mock(spec=Request)
    mock_response = Mock(spec=Response)
    mock_response.headers = {}
    
    async def mock_call_next(request):
        return mock_response
    
    # Test middleware execution
    response = await middleware.dispatch(mock_request, mock_call_next)
    assert response.headers is not None

@pytest.mark.asyncio
async def test_middleware_order(app, test_client):
    """Test middleware execution order"""
    execution_order = []
    
    class TestMiddleware1:
        async def __call__(self, request, call_next):
            execution_order.append(1)
            response = await call_next(request)
            return response
    
    class TestMiddleware2:
        async def __call__(self, request, call_next):
            execution_order.append(2)
            response = await call_next(request)
            return response
    
    app.add_middleware(TestMiddleware1)
    app.add_middleware(TestMiddleware2)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    response = test_client.get("/test")
    assert response.status_code == 200
    assert execution_order == [2, 1]  # Middleware executes in reverse order

@pytest.mark.asyncio
async def test_cache_middleware_invalidation(app, test_client):
    """Test cache middleware invalidation"""
    app.add_middleware(CacheMiddleware)
    
    test_data = {"message": "test"}
    updated_data = {"message": "updated"}
    
    @app.get("/test")
    async def test_endpoint():
        return test_data
    
    # First request
    response1 = test_client.get("/test")
    assert response1.json() == test_data
    
    # Invalidate cache
    cache_key = f"cache:GET:/test:"
    await cache_manager.delete(cache_key)
    
    # Update test data
    test_data.update(updated_data)
    
    # Second request should get updated data
    response2 = test_client.get("/test")
    assert response2.json() == updated_data

@pytest.mark.asyncio
async def test_rate_limit_middleware_tiers(app, test_client):
    """Test rate limiting middleware with different tiers"""
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    # Test different tiers
    tiers = ["free", "basic", "premium"]
    for tier in tiers:
        # Mock organization with tier
        with patch("app.api.core.middleware.getattr") as mock_getattr:
            mock_org = Mock()
            mock_org.tier = tier
            mock_getattr.return_value = mock_org
            
            # Make requests up to tier limit
            limit = settings.tier_limits[tier]
            for _ in range(limit):
                response = test_client.get("/test")
                assert response.status_code == 200
            
            # Next request should be rate limited
            response = test_client.get("/test")
            assert response.status_code == 429 