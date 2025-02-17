import pytest
from prometheus_client import REGISTRY
from app.api.core.metrics import (
    MetricsCollector,
    http_requests_total,
    http_request_duration_seconds,
    db_connections_current,
    db_query_duration_seconds,
    cache_hits_total,
    cache_misses_total,
    rate_limit_hits_total,
    events_processed_total,
    api_component_health,
    data_quality_status
)

@pytest.fixture
def metrics_collector():
    """Create a test metrics collector instance"""
    return MetricsCollector()

def get_metric_value(metric, labels=None):
    """Helper function to get metric value"""
    if labels:
        return metric.labels(**labels)._value.get()
    return metric._value.get()

@pytest.mark.asyncio
async def test_track_request(metrics_collector):
    """Test tracking HTTP request metrics"""
    method = "GET"
    endpoint = "/test"
    status = 200
    duration = 0.5
    
    # Track request
    metrics_collector.track_request(method, endpoint, status, duration)
    
    # Verify request count
    assert get_metric_value(
        http_requests_total,
        {"method": method, "endpoint": endpoint, "status": status}
    ) == 1
    
    # Verify request duration
    assert get_metric_value(
        http_request_duration_seconds,
        {"method": method, "endpoint": endpoint}
    ) > 0

@pytest.mark.asyncio
async def test_track_db_connections(metrics_collector):
    """Test tracking database connection metrics"""
    database = "postgres"
    connections = 5
    
    # Track connections
    metrics_collector.track_db_connections(database, connections)
    
    # Verify connection count
    assert get_metric_value(
        db_connections_current,
        {"database": database}
    ) == connections

@pytest.mark.asyncio
async def test_track_db_query(metrics_collector):
    """Test tracking database query metrics"""
    database = "postgres"
    operation = "SELECT"
    duration = 0.1
    
    # Track query
    metrics_collector.track_db_query(database, operation, duration)
    
    # Verify query duration
    assert get_metric_value(
        db_query_duration_seconds,
        {"database": database, "operation": operation}
    ) > 0

@pytest.mark.asyncio
async def test_track_cache_operations(metrics_collector):
    """Test tracking cache operation metrics"""
    cache = "redis"
    
    # Track cache hit
    metrics_collector.track_cache_hit(cache)
    assert get_metric_value(cache_hits_total, {"cache": cache}) == 1
    
    # Track cache miss
    metrics_collector.track_cache_miss(cache)
    assert get_metric_value(cache_misses_total, {"cache": cache}) == 1

@pytest.mark.asyncio
async def test_track_rate_limit_hit(metrics_collector):
    """Test tracking rate limit hit metrics"""
    tier = "basic"
    
    # Track rate limit hit
    metrics_collector.track_rate_limit_hit(tier)
    
    # Verify rate limit hit count
    assert get_metric_value(rate_limit_hits_total, {"tier": tier}) == 1

@pytest.mark.asyncio
async def test_track_event_processing(metrics_collector):
    """Test tracking event processing metrics"""
    event_type = "user_event"
    status = "success"
    duration = 0.2
    
    # Track event processing
    metrics_collector.track_event_processing(event_type, status, duration)
    
    # Verify event count
    assert get_metric_value(
        events_processed_total,
        {"type": event_type, "status": status}
    ) == 1

@pytest.mark.asyncio
async def test_track_component_health(metrics_collector):
    """Test tracking component health metrics"""
    component = "api"
    
    # Track healthy component
    metrics_collector.track_component_health(component, True)
    assert get_metric_value(api_component_health, {"component": component}) == 1
    
    # Track unhealthy component
    metrics_collector.track_component_health(component, False)
    assert get_metric_value(api_component_health, {"component": component}) == 0

@pytest.mark.asyncio
async def test_track_data_quality(metrics_collector):
    """Test tracking data quality metrics"""
    component = "events"
    status = 2  # healthy
    
    # Track data quality
    metrics_collector.track_data_quality(component, status)
    
    # Verify data quality status
    assert get_metric_value(data_quality_status, {"component": component}) == status

@pytest.mark.asyncio
async def test_track_resource_usage(metrics_collector):
    """Test tracking resource usage metrics"""
    cpu_percent = 50.0
    memory_used = 1024 * 1024 * 100  # 100MB
    memory_total = 1024 * 1024 * 1000  # 1GB
    
    # Track resource usage
    metrics_collector.track_resource_usage(
        cpu_percent=cpu_percent,
        memory_used=memory_used,
        memory_total=memory_total
    )
    
    # Verify CPU usage
    assert get_metric_value(
        cpu_usage_percent,
        {"cpu": "total"}
    ) == cpu_percent
    
    # Verify memory usage
    assert get_metric_value(
        memory_usage_bytes,
        {"type": "used"}
    ) == memory_used
    assert get_metric_value(
        memory_usage_bytes,
        {"type": "total"}
    ) == memory_total

@pytest.mark.asyncio
async def test_track_error(metrics_collector):
    """Test tracking error metrics"""
    error_type = "validation_error"
    
    # Track error
    metrics_collector.track_error(error_type)
    
    # Verify error metrics
    assert get_metric_value(
        validation_errors,
        {"error_type": error_type}
    ) == 1
    assert get_metric_value(
        error_handling_validation,
        {"status": "failed"}
    ) == 1
    assert get_metric_value(
        error_recovery_attempts,
        {"error_type": error_type, "status": "started"}
    ) == 1

@pytest.mark.asyncio
async def test_metrics_registry(metrics_collector):
    """Test metrics are properly registered"""
    # Get all registered metrics
    metrics = list(REGISTRY.collect())
    
    # Verify essential metrics are registered
    metric_names = [metric.name for metric in metrics]
    assert "http_requests_total" in metric_names
    assert "http_request_duration_seconds" in metric_names
    assert "db_connections_current" in metric_names
    assert "cache_hits_total" in metric_names
    assert "rate_limit_hits_total" in metric_names 