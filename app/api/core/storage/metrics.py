from typing import Dict, Optional
from prometheus_client import Counter, Histogram, Gauge

# Query metrics
query_duration = Histogram(
    "storage_query_duration_seconds",
    "Duration of database queries in seconds",
    ["database", "operation"]
)

query_errors = Counter(
    "storage_query_errors_total",
    "Total number of failed database queries",
    ["database", "operation", "error_type"]
)

query_total = Counter(
    "storage_query_total",
    "Total number of database queries",
    ["database", "operation"]
)

# Connection pool metrics
pool_size = Gauge(
    "storage_pool_size",
    "Current size of the connection pool",
    ["database"]
)

pool_available = Gauge(
    "storage_pool_available",
    "Number of available connections in the pool",
    ["database"]
)

pool_in_use = Gauge(
    "storage_pool_in_use",
    "Number of connections currently in use",
    ["database"]
)

# Cache metrics
cache_hits = Counter(
    "storage_cache_hits_total",
    "Total number of cache hits",
    ["cache"]
)

cache_misses = Counter(
    "storage_cache_misses_total",
    "Total number of cache misses",
    ["cache"]
)

cache_size = Gauge(
    "storage_cache_size",
    "Current size of the cache",
    ["cache"]
)

# Export all metrics
metrics: Dict[str, object] = {
    "query_duration": query_duration,
    "query_errors": query_errors,
    "query_total": query_total,
    "pool_size": pool_size,
    "pool_available": pool_available,
    "pool_in_use": pool_in_use,
    "cache_hits": cache_hits,
    "cache_misses": cache_misses,
    "cache_size": cache_size,
} 