from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry
from typing import Dict, Any, Optional
import time
import logging
from .base_metrics import BaseMetrics

logger = logging.getLogger(__name__)

# Create a custom registry for our metrics
REGISTRY = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],  # Define duration buckets
    registry=REGISTRY
)

# Database metrics
db_connections_current = Gauge(
    "db_connections_current",
    "Current number of database connections",
    ["database"],
    registry=REGISTRY
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["database", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=REGISTRY
)

# Query Optimization metrics
query_patterns_total = Counter(
    "query_patterns_total",
    "Total number of unique query patterns",
    ["database"]
)

query_optimizations_total = Counter(
    "query_optimizations_total",
    "Total number of query optimizations",
    ["database", "status"]
)

slow_queries_total = Counter(
    "slow_queries_total",
    "Total number of slow queries detected",
    ["database", "pattern"]
)

optimization_recommendations_total = Counter(
    "optimization_recommendations_total",
    "Total number of optimization recommendations",
    ["database", "type", "priority"]
)

query_pattern_executions = Counter(
    "query_pattern_executions_total",
    "Total number of query pattern executions",
    ["database", "pattern"]
)

query_pattern_duration = Histogram(
    "query_pattern_duration_seconds",
    "Query pattern execution duration",
    ["database", "pattern"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Cache metrics
cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache"]
)

# Rate limiting metrics
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total number of rate limit hits",
    ["tier"]
)

# Business metrics
events_processed_total = Counter(
    "events_processed_total",
    "Total number of events processed",
    ["type", "status"]
)

event_processing_duration_seconds = Histogram(
    "event_processing_duration_seconds",
    "Event processing duration in seconds",
    ["type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# System metrics
system_info = Info("system", "System information")

# API Validation metrics
api_component_health = Gauge(
    "api_component_health",
    "Health status of API components",
    ["component"]
)

api_validation_issues = Counter(
    "api_validation_issues_total",
    "Total number of API validation issues",
    ["component", "type"]
)

rate_limit_validation = Counter(
    "rate_limit_validation_total",
    "Rate limit validation results",
    ["status"]
)

auth_validation = Counter(
    "auth_validation_total",
    "Authentication validation results",
    ["status"]
)

validation_errors = Counter(
    "validation_errors_total",
    "Validation error counts by type",
    ["error_type"]
)

error_handling_validation = Counter(
    "error_handling_validation_total",
    "Error handling validation results",
    ["status"]
)

message_queue_validation = Gauge(
    "message_queue_validation",
    "Message queue validation status",
    ["component"]
)

api_validation_status = Gauge(
    "api_validation_status",
    "Overall API validation status",
    ["status"]
)

# Data freshness metrics
data_freshness_seconds = Gauge(
    "data_freshness_seconds",
    "Data freshness in seconds by source",
    ["source"]
)

schema_changes_total = Counter(
    "schema_changes_total",
    "Total number of schema changes detected",
    ["source"]
)

data_quality_status = Gauge(
    "data_quality_status",
    "Overall data quality status (0=unhealthy, 1=degraded, 2=healthy)",
    ["component"]
)

# Error Recovery metrics
error_recovery_attempts = Counter(
    "error_recovery_attempts_total",
    "Total number of error recovery attempts",
    ["error_type", "status"]
)

error_recovery_duration = Histogram(
    "error_recovery_duration_seconds",
    "Duration of error recovery attempts",
    ["error_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

error_recovery_success_rate = Gauge(
    "error_recovery_success_rate",
    "Success rate of error recovery attempts",
    ["error_type"]
)

# Resource metrics
cpu_usage_percent = Gauge(
    "cpu_usage_percent",
    "CPU usage percentage",
    ["cpu"]
)

memory_usage_bytes = Gauge(
    "memory_usage_bytes",
    "Memory usage in bytes",
    ["type"]  # used, total, swap
)

disk_usage_bytes = Gauge(
    "disk_usage_bytes",
    "Disk usage in bytes",
    ["type"]  # used, total, read, write
)

network_usage_bytes = Counter(
    "network_usage_bytes",
    "Network usage in bytes",
    ["direction"]  # sent, received
)

# Database error metrics
db_errors_total = Counter(
    "db_errors_total",
    "Total number of database errors",
    ["database", "type"]
)

# Component health metrics
component_health = Gauge(
    "component_health",
    "Health status of components (0=unhealthy, 1=healthy)",
    ["component"],
    registry=REGISTRY
)

class PrometheusMetrics(BaseMetrics):
    """Prometheus implementation of metrics collection"""
    
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        """Track health status of a component"""
        component_health.labels(component=component).set(1 if is_healthy else 0)
    
    def track_db_connection_count(self, database: str, count: int) -> None:
        """Track number of database connections"""
        db_connections_current.labels(database=database).set(count)
    
    def track_query_duration(self, database: str, operation: str, duration: float) -> None:
        """Track duration of database queries"""
        db_query_duration_seconds.labels(
            database=database,
            operation=operation
        ).observe(duration)

    def track_error(self, error_type: str) -> None:
        """Track error occurrence"""
        validation_errors.labels(error_type=error_type).inc()
        error_handling_validation.labels(status="failed").inc()
        error_recovery_attempts.labels(error_type=error_type, status="started").inc()

    def track_cache_miss(self, cache: str) -> None:
        """Track cache miss"""
        cache_misses_total.labels(cache=cache).inc()

    def track_cache_hit(self, cache: str) -> None:
        """Track cache hit"""
        cache_hits_total.labels(cache=cache).inc()

    def track_rate_limit_hit(self, tier: str) -> None:
        """Track rate limit hit"""
        rate_limit_hits_total.labels(tier=tier).inc()

    def track_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """Track HTTP request"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

# Global metrics instance
metrics = PrometheusMetrics() 