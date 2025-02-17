import pytest
import asyncio
from httpx import AsyncClient
from ..api.core.database_pool import db_pool
from ..api.core.cache import cache_manager
from ..api.core.circuit_breaker import circuit_breakers
from ..api.core.query_optimizer import query_optimizer
from ..api.core.metrics import metrics
import time
import json

@pytest.mark.asyncio
async def test_database_pool_initialization():
    """Test database pool initialization and health"""
    # Initialize pools
    await db_pool.init_pools()
    
    # Check PostgreSQL pool
    postgres_stats = await db_pool.get_pool_stats("postgres")
    assert postgres_stats["total_connections"] >= db_pool.pool_config["postgres"]["min_size"]
    
    # Check ClickHouse pool
    clickhouse_stats = await db_pool.get_pool_stats("clickhouse")
    assert clickhouse_stats["total_connections"] == db_pool.pool_config["clickhouse"]["min_size"]
    
    # Check pool health
    postgres_health = await db_pool.check_pool_health("postgres")
    assert postgres_health["status"] == "healthy"
    assert "latency" in postgres_health
    
    clickhouse_health = await db_pool.check_pool_health("clickhouse")
    assert clickhouse_health["status"] == "healthy"
    assert "latency" in clickhouse_health
    
    # Cleanup
    await db_pool.cleanup()

@pytest.mark.asyncio
async def test_circuit_breaker_functionality():
    """Test circuit breaker behavior"""
    breaker = circuit_breakers["postgres"]
    
    # Test successful calls
    for _ in range(3):
        result = await breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state.value == "closed"
    
    # Test failure behavior
    failure_count = 0
    for _ in range(6):
        try:
            await breaker.call(lambda: 1/0)  # Force an error
        except ZeroDivisionError:
            failure_count += 1
    
    assert failure_count == 6
    assert breaker.state.value == "open"
    
    # Test recovery
    await asyncio.sleep(breaker.recovery_timeout)
    
    # Should be in half-open state after timeout
    assert breaker.state.value == "half_open"
    
    # Successful call should close the circuit
    result = await breaker.call(lambda: "recovered")
    assert result == "recovered"
    assert breaker.state.value == "closed"

@pytest.mark.asyncio
async def test_cache_management():
    """Test cache management functionality"""
    # Test cache set and get
    test_key = "test:key"
    test_data = {"message": "test"}
    
    success = await cache_manager.set(test_key, test_data)
    assert success is True
    
    cached_data = await cache_manager.get(test_key)
    assert cached_data == test_data
    
    # Test pattern-based invalidation
    pattern = "test:*"
    invalidated = await cache_manager.invalidate(pattern)
    assert invalidated > 0
    
    # Verify data is invalidated
    cached_data = await cache_manager.get(test_key)
    assert cached_data is None
    
    # Test cache warm-up
    async def warm_up_func():
        return {"warmed": "up"}
    
    await cache_manager.register_warm_up_query("warm:key", warm_up_func)
    await cache_manager.warm_up_cache()
    
    warmed_data = await cache_manager.get("warm:key")
    assert warmed_data == {"warmed": "up"}
    
    # Test eviction policy
    stats_before = await cache_manager.get_stats()
    await cache_manager.evict_entries(target_memory_usage=0)  # Force eviction
    stats_after = await cache_manager.get_stats()
    
    assert stats_after["total_keys"] < stats_before["total_keys"]

@pytest.mark.asyncio
async def test_query_optimization():
    """Test query optimization functionality"""
    # Test query analysis
    test_query = "SELECT * FROM users"
    analysis = await query_optimizer.analyze_query(test_query)
    
    assert "plan" in analysis
    assert "metrics" in analysis
    assert "recommendations" in analysis
    
    # Test query tracking
    await query_optimizer.track_query_performance(
        query=test_query,
        duration=1.5,  # Slow query
        rows_affected=100
    )
    
    stats = await query_optimizer.get_query_stats()
    assert stats["total_queries"] > 0
    assert stats["slow_queries"] > 0
    
    # Test query optimization
    optimization = await query_optimizer.optimize_query(test_query)
    assert "recommendations" in optimization
    assert any("SELECT *" in rec for rec in optimization["recommendations"])

@pytest.mark.asyncio
async def test_metrics_collection():
    """Test metrics collection"""
    # Track various metrics
    metrics.track_request("GET", "/test", 200, 0.1)
    metrics.track_cache_hit("redis")
    metrics.track_db_query("postgres", "query", 0.05)
    
    # Verify metrics are collected
    assert metrics.http_requests_total._value.get(("GET", "/test", "200")) == 1
    assert metrics.cache_hits_total._value.get(("redis",)) == 1
    assert metrics.db_query_duration_seconds._count.get(("postgres", "query")) == 1

@pytest.mark.asyncio
async def test_system_integration(client: AsyncClient):
    """Test full system integration"""
    # Test health endpoint
    response = await client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    
    assert health_data["status"] in ["healthy", "unhealthy"]
    assert "services" in health_data
    
    # Test rate limiting
    for _ in range(1100):  # Exceed rate limit
        response = await client.get("/health")
    
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    
    # Test caching
    response1 = await client.get("/health")
    response2 = await client.get("/health")
    
    assert response1.headers.get("X-Cache-Hit") is None
    assert response2.headers.get("X-Cache-Hit") == "true"
    
    # Test security headers
    security_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Strict-Transport-Security",
        "Content-Security-Policy"
    ]
    
    for header in security_headers:
        assert header in response1.headers 