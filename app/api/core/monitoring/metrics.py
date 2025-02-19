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

# Database Metrics
db_connection_failures = Counter(
    'db_connection_failures_total',
    'Number of database connection failures',
    ['database']
)

db_operation_duration = Histogram(
    'db_operation_duration_seconds',
    'Duration of database operations',
    ['database', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

db_pool_connections = Gauge(
    'db_pool_connections',
    'Number of connections in the pool',
    ['database', 'state']
)

# Recovery Metrics
recovery_attempts = Counter(
    'recovery_attempts_total',
    'Number of recovery attempts',
    ['operation']
)

recovery_success = Counter(
    'recovery_success_total',
    'Number of successful recoveries',
    ['operation']
)

recovery_failure = Counter(
    'recovery_failure_total',
    'Number of failed recoveries',
    ['operation']
)

recovery_duration = Histogram(
    'recovery_duration_seconds',
    'Duration of recovery operations',
    ['operation'],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0)
)

# Data Sync Metrics
sync_operations = Counter(
    'sync_operations_total',
    'Number of sync operations',
    ['source_type', 'status']
)

sync_duration = Histogram(
    'sync_duration_seconds',
    'Duration of sync operations',
    ['source_type'],
    buckets=(10.0, 30.0, 60.0, 180.0, 300.0)
)

sync_records_processed = Counter(
    'sync_records_processed_total',
    'Number of records processed during sync',
    ['source_type', 'operation']
)

sync_errors = Counter(
    'sync_errors_total',
    'Number of sync errors',
    ['source_type', 'error_type']
)

sync_recovery_attempts = Counter(
    'sync_recovery_attempts_total',
    'Number of sync recovery attempts',
    ['source_type']
)

sync_recovery_success = Counter(
    'sync_recovery_success_total',
    'Number of successful sync recoveries',
    ['source_type']
)

sync_recovery_duration = Histogram(
    'sync_recovery_duration_seconds',
    'Duration of sync recovery operations',
    ['source_type'],
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0)
)

# Pipeline Metrics
pipeline_operations = Counter(
    'pipeline_operations_total',
    'Number of pipeline operations',
    ['pipeline_type', 'status']
)

pipeline_duration = Histogram(
    'pipeline_duration_seconds',
    'Duration of pipeline operations',
    ['pipeline_type'],
    buckets=(10.0, 30.0, 60.0, 180.0, 300.0)
)

pipeline_errors = Counter(
    'pipeline_errors_total',
    'Number of pipeline errors',
    ['pipeline_type', 'error_type']
)

# Health Check Metrics
health_check_status = Gauge(
    'health_check_status',
    'Status of health checks',
    ['component']
)

health_check_duration = Histogram(
    'health_check_duration_seconds',
    'Duration of health checks',
    ['component'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

class PrometheusMetrics(BaseMetrics):
    """Prometheus metrics implementation."""
    
    def __init__(self):
        """Initialize Prometheus metrics."""
        # Create a custom registry
        self.registry = CollectorRegistry()
        
        # Component health metrics
        self.component_health = Gauge(
            'component_health',
            'Health status of system components',
            ['component'],
            registry=self.registry
        )
        
        # Request metrics
        self.request_latency = Histogram(
            'request_latency_seconds',
            'Request latency in seconds',
            ['endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        # Error metrics
        self.error_counter = Counter(
            'error_total',
            'Total number of errors',
            ['error_type'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_query_latency = Histogram(
            'database_query_latency_seconds',
            'Database query latency in seconds',
            ['database', 'query_type'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )

        # Retry metrics
        self.retry_attempts = Counter(
            'retry_attempts_total',
            'Total number of retry attempts',
            ['operation', 'attempt'],
            registry=self.registry
        )
        
        self.retry_success = Counter(
            'retry_success_total',
            'Total number of successful retries',
            ['operation'],
            registry=self.registry
        )
        
        self.retry_failure = Counter(
            'retry_failure_total',
            'Total number of failed retries',
            ['operation'],
            registry=self.registry
        )
        
        self.retry_delay = Histogram(
            'retry_delay_seconds',
            'Retry delay in seconds',
            ['operation'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )

        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=half-open, 2=open)',
            ['breaker'],
            registry=self.registry
        )
        
        self.circuit_breaker_failures = Counter(
            'circuit_breaker_failures_total',
            'Total number of circuit breaker failures',
            ['breaker'],
            registry=self.registry
        )
        
        self.circuit_breaker_trips = Counter(
            'circuit_breaker_trips_total',
            'Total number of times circuit breaker has tripped',
            ['breaker'],
            registry=self.registry
        )

        # System metrics
        self.cpu_usage_percent = Gauge(
            "cpu_usage_percent",
            "CPU usage percentage",
            ["cpu"],
            registry=REGISTRY
        )
        self.memory_usage_bytes = Gauge(
            "memory_usage_bytes",
            "Memory usage in bytes",
            ["type"],
            registry=REGISTRY
        )
        self.memory_usage_percent = Gauge(
            "memory_usage_percent",
            "Memory usage percentage",
            registry=REGISTRY
        )
        self.disk_usage_bytes = Gauge(
            "disk_usage_bytes",
            "Disk usage in bytes",
            ["type"],
            registry=REGISTRY
        )
        self.disk_usage_percent = Gauge(
            "disk_usage_percent",
            "Disk usage percentage",
            registry=REGISTRY
        )
        self.network_bytes_sent = Gauge(
            "network_bytes_sent",
            "Network bytes sent",
            registry=REGISTRY
        )
        self.network_bytes_received = Gauge(
            "network_bytes_received",
            "Network bytes received",
            registry=REGISTRY
        )
    
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        """Track health status of a component."""
        try:
            self.component_health.labels(component=component).set(1 if is_healthy else 0)
        except Exception as e:
            logger.error(f"Error tracking component health: {str(e)}")
    
    def track_request_latency(self, endpoint: str, latency: float) -> None:
        """Track request latency for an endpoint."""
        try:
            self.request_latency.labels(endpoint=endpoint).observe(latency)
        except Exception as e:
            logger.error(f"Error tracking request latency: {str(e)}")
    
    def track_error(self, error_type: str, error_message: str) -> None:
        """Track an error occurrence."""
        try:
            self.error_counter.labels(error_type=error_type).inc()
            logger.error(f"{error_type}: {error_message}")
        except Exception as e:
            logger.error(f"Error tracking error: {str(e)}")
    
    def track_database_query(self, database: str, query_type: str, latency: float) -> None:
        """Track database query metrics."""
        try:
            self.db_query_latency.labels(
                database=database,
                query_type=query_type
            ).observe(latency)
        except Exception as e:
            logger.error(f"Error tracking database query: {str(e)}")

    def track_retry_attempt(self, operation: str, attempt: int, delay: float, error: str) -> None:
        """Track a retry attempt."""
        try:
            self.retry_attempts.labels(
                operation=operation,
                attempt=str(attempt)
            ).inc()
            self.retry_delay.labels(operation=operation).observe(delay)
            logger.info(f"Retry attempt {attempt} for {operation}: {error}")
        except Exception as e:
            logger.error(f"Error tracking retry attempt: {str(e)}")

    def track_retry_success(self, operation: str, attempts: int, total_delay: float) -> None:
        """Track a successful retry."""
        try:
            self.retry_success.labels(operation=operation).inc()
            logger.info(f"Retry succeeded for {operation} after {attempts} attempts")
        except Exception as e:
            logger.error(f"Error tracking retry success: {str(e)}")

    def track_retry_failure(self, operation: str, attempts: int, total_delay: float, error: str) -> None:
        """Track a failed retry."""
        try:
            self.retry_failure.labels(operation=operation).inc()
            logger.error(f"Retry failed for {operation} after {attempts} attempts: {error}")
        except Exception as e:
            logger.error(f"Error tracking retry failure: {str(e)}")

    def track_circuit_breaker_state(self, breaker: str, state: str) -> None:
        """Track circuit breaker state changes."""
        try:
            state_value = {
                "closed": 0,
                "half-open": 1,
                "open": 2
            }.get(state, 0)
            self.circuit_breaker_state.labels(breaker=breaker).set(state_value)
            logger.info(f"Circuit breaker {breaker} state changed to {state}")
        except Exception as e:
            logger.error(f"Error tracking circuit breaker state: {str(e)}")

    def track_circuit_breaker_failure(self, breaker: str) -> None:
        """Track circuit breaker failures."""
        try:
            self.circuit_breaker_failures.labels(breaker=breaker).inc()
        except Exception as e:
            logger.error(f"Error tracking circuit breaker failure: {str(e)}")

    def track_circuit_breaker_trip(self, breaker: str) -> None:
        """Track circuit breaker trips."""
        try:
            self.circuit_breaker_trips.labels(breaker=breaker).inc()
            logger.warning(f"Circuit breaker {breaker} tripped")
        except Exception as e:
            logger.error(f"Error tracking circuit breaker trip: {str(e)}")
    
    def get_registry(self) -> CollectorRegistry:
        """Get the metrics registry."""
        return self.registry

# Global metrics instance
metrics = PrometheusMetrics()

def track_recovery_attempt(operation: str) -> None:
    """Track a recovery attempt."""
    recovery_attempts.labels(operation=operation).inc()

def track_recovery_success(operation: str) -> None:
    """Track a successful recovery."""
    recovery_success.labels(operation=operation).inc()

def track_recovery_failure(operation: str) -> None:
    """Track a failed recovery."""
    recovery_failure.labels(operation=operation).inc()

def track_recovery_duration(operation: str, duration: float) -> None:
    """Track recovery operation duration."""
    recovery_duration.labels(operation=operation).observe(duration)

def track_sync_operation(source_type: str, status: str) -> None:
    """Track a sync operation."""
    sync_operations.labels(source_type=source_type, status=status).inc()

def track_sync_duration(source_type: str, duration: float) -> None:
    """Track sync operation duration."""
    sync_duration.labels(source_type=source_type).observe(duration)

def track_sync_records(source_type: str, operation: str, count: int) -> None:
    """Track number of records processed during sync."""
    sync_records_processed.labels(
        source_type=source_type,
        operation=operation
    ).inc(count)

def track_sync_error(source_type: str, error_type: str) -> None:
    """Track a sync error."""
    sync_errors.labels(source_type=source_type, error_type=error_type).inc()

def track_sync_recovery_attempt(source_type: str) -> None:
    """Track a sync recovery attempt."""
    sync_recovery_attempts.labels(source_type=source_type).inc()

def track_sync_recovery_success(source_type: str) -> None:
    """Track a successful sync recovery."""
    sync_recovery_success.labels(source_type=source_type).inc()

def track_sync_recovery_duration(source_type: str, duration: float) -> None:
    """Track sync recovery operation duration."""
    sync_recovery_duration.labels(source_type=source_type).observe(duration)

def track_pipeline_operation(pipeline_type: str, status: str) -> None:
    """Track a pipeline operation."""
    pipeline_operations.labels(
        pipeline_type=pipeline_type,
        status=status
    ).inc()

def track_pipeline_duration(pipeline_type: str, duration: float) -> None:
    """Track pipeline operation duration."""
    pipeline_duration.labels(pipeline_type=pipeline_type).observe(duration)

def track_pipeline_error(pipeline_type: str, error_type: str) -> None:
    """Track a pipeline error."""
    pipeline_errors.labels(
        pipeline_type=pipeline_type,
        error_type=error_type
    ).inc()

def track_health_check(component: str, status: float, duration: float) -> None:
    """Track health check results."""
    health_check_status.labels(component=component).set(status)
    health_check_duration.labels(component=component).observe(duration)

__all__ = [
    'track_recovery_attempt',
    'track_recovery_success',
    'track_recovery_failure',
    'track_recovery_duration',
    'track_sync_operation',
    'track_sync_duration',
    'track_sync_records',
    'track_sync_error',
    'track_sync_recovery_attempt',
    'track_sync_recovery_success',
    'track_sync_recovery_duration',
    'track_pipeline_operation',
    'track_pipeline_duration',
    'track_pipeline_error',
    'track_health_check'
] 