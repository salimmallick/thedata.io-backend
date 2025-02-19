from typing import List, Dict, Any, Optional
import asyncio
import asyncpg
from ..core.config.settings import settings
from ..models.timeseries import (
    MaterializedView,
    MaterializedAggregation,
    TimeseriesData,
    AggregationType,
    TimeWindow
)
import logging
from datetime import datetime, timedelta
from ..core.database import db_pool, DatabaseError
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
QUERY_DURATION = Histogram(
    'materialize_query_duration_seconds',
    'Duration of Materialize queries',
    ['query_type']
)
QUERY_ERRORS = Counter(
    'materialize_query_errors_total',
    'Total number of Materialize query errors',
    ['error_type']
)
VIEW_REFRESH_TIME = Histogram(
    'materialize_view_refresh_seconds',
    'Time taken to refresh materialized views',
    ['view_name']
)
ACTIVE_CONNECTIONS = Gauge(
    'materialize_active_connections',
    'Number of active Materialize connections'
)

class MaterializedView:
    """Represents a materialized view in Materialize"""
    def __init__(
        self,
        name: str,
        query: str,
        refresh_interval: Optional[str] = None,
        partition_key: Optional[str] = None,
        indexes: Optional[List[str]] = None,
        cluster_key: Optional[str] = None
    ):
        self.name = name
        self.query = query
        self.refresh_interval = refresh_interval or "1 minute"
        self.last_refresh = None
        self.partition_key = partition_key
        self.indexes = indexes or []
        self.cluster_key = cluster_key
        self.performance_stats = {
            "avg_refresh_time": 0,
            "total_refreshes": 0,
            "last_refresh_time": None,
            "error_count": 0
        }

class MaterializedAggregation:
    """Represents a real-time aggregation in Materialize"""
    def __init__(
        self,
        name: str,
        source: str,
        dimensions: List[str],
        metrics: Dict[str, str],
        window_size: Optional[str] = None,
        retention_hours: Optional[int] = None
    ):
        self.name = name
        self.source = source
        self.dimensions = dimensions
        self.metrics = metrics
        self.window_size = window_size
        self.retention_hours = retention_hours
        self.performance_stats = {
            "avg_processing_time": 0,
            "total_records": 0,
            "last_update": None
        }

class MaterializeService:
    """Service for interacting with Materialize."""
    
    def __init__(self):
        """Initialize Materialize service."""
        self._cleanup_task = None
        # Track active connections
        ACTIVE_CONNECTIONS.set_function(lambda: db_pool.get_active_connections())
    
    async def start(self):
        """Start the service and initialize cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def stop(self):
        """Stop the service and cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against Materialize with monitoring."""
        try:
            with QUERY_DURATION.labels(query_type=query.split()[0].lower()).time():
                async with db_pool.postgres_connection() as conn:
                    # Convert dict params to list if provided
                    if params:
                        param_list = [params[key] for key in sorted(params.keys())]
                        result = await conn.fetch(query, *param_list)
                    else:
                        result = await conn.fetch(query)
                    
                    return [dict(row) for row in result]
                    
        except Exception as e:
            error_type = type(e).__name__
            QUERY_ERRORS.labels(error_type=error_type).inc()
            logger.error(f"Error executing Materialize query: {e}")
            raise
    
    async def create_materialized_view(self, view: MaterializedView) -> None:
        """Create a materialized view with monitoring."""
        try:
            # Drop existing view if it exists
            drop_query = f"DROP MATERIALIZED VIEW IF EXISTS {view.name}"
            await self.execute_query(drop_query)
            
            # Create new view
            create_query = f"""
            CREATE MATERIALIZED VIEW {view.name} 
            WITH (
                refresh_interval = '{view.refresh_interval}'
                {f", partition_key = '{view.partition_key}'" if view.partition_key else ""}
                {f", cluster_key = '{view.cluster_key}'" if view.cluster_key else ""}
            )
            AS {view.query}
            """
            await self.execute_query(create_query)
            
            # Create indexes
            for index in view.indexes:
                index_query = f"CREATE INDEX ON {view.name} ({index})"
                await self.execute_query(index_query)
            
            logger.info(f"Successfully created materialized view: {view.name}")
        except Exception as e:
            logger.error(f"Error creating materialized view {view.name}: {e}")
            raise
    
    async def refresh_materialized_view(self, view_name: str) -> None:
        """Refresh a materialized view with monitoring."""
        try:
            with VIEW_REFRESH_TIME.labels(view_name=view_name).time():
                query = f"REFRESH MATERIALIZED VIEW {view_name}"
                await self.execute_query(query)
            logger.info(f"Successfully refreshed materialized view: {view_name}")
        except Exception as e:
            logger.error(f"Error refreshing materialized view {view_name}: {e}")
            raise
    
    async def get_view_stats(self, view_name: str) -> Dict[str, Any]:
        """Get statistics for a materialized view."""
        query = """
        SELECT 
            name,
            type,
            creation_time,
            definition
        FROM mz_catalog.mz_views
        WHERE name = $1
        """
        result = await self.execute_query(query, {"name": view_name})
        return result[0] if result else {}
    
    async def cleanup_stale_views(self, max_age_hours: int = 24) -> None:
        """Clean up stale materialized views."""
        try:
            # Query for materialized views directly
            query = """
            SELECT name, id
            FROM mz_catalog.mz_materialized_views
            """
            views = await self.execute_query(query)
            
            for view in views:
                logger.info(f"Found view: {view.get('name')}")
                # For now, don't drop any views until we figure out the correct schema
                # await self.execute_query(f"DROP MATERIALIZED VIEW IF EXISTS {view.get('name')}")
        except Exception as e:
            logger.error(f"Error cleaning up stale views: {e}")
            raise
    
    async def _periodic_cleanup(self):
        """Periodically clean up stale views."""
        while True:
            try:
                await self.cleanup_stale_views()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(3600)  # Run every hour

# Create a singleton instance
materialize_service = MaterializeService() 