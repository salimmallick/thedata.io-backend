"""
Monitoring service for metrics collection and reporting.
"""
import asyncio
from typing import Dict, Any, Optional
from prometheus_client import start_http_server
from .config import settings
from .metrics import (
    track_sync_operation,
    track_sync_duration,
    track_sync_records,
    track_sync_error,
    track_sync_recovery_attempt,
    track_sync_recovery_success,
    track_sync_recovery_duration,
    track_health_check
)
from ..logging.logger import logger
from ..instances import init_monitoring_instances
from .health import HealthChecker

class MonitoringService:
    """Service for managing metrics collection and reporting."""
    
    def __init__(self):
        """Initialize the monitoring service."""
        self._running = False
        self._tasks = []
        self._health_checker = HealthChecker()
    
    async def start(self) -> None:
        """Start the monitoring service."""
        if self._running:
            return
        
        try:
            # Initialize health checker
            init_monitoring_instances(health_checker_instance=self._health_checker)
            
            # Start Prometheus HTTP server
            if settings.PROMETHEUS_ENABLED:
                start_http_server(
                    port=settings.PROMETHEUS_PORT,
                    addr='0.0.0.0'
                )
                logger.info(
                    f"Started Prometheus metrics server on port {settings.PROMETHEUS_PORT}"
                )
            
            # Start health check task
            self._tasks.append(
                asyncio.create_task(self._health_check_loop())
            )
            
            # Start metric collection task
            self._tasks.append(
                asyncio.create_task(self._metric_collection_loop())
            )
            
            self._running = True
            logger.info("Monitoring service started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring service: {str(e)}")
            raise
    
    async def stop(self) -> None:
        """Stop the monitoring service."""
        if not self._running:
            return
        
        try:
            # Cancel all tasks
            for task in self._tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
            self._tasks = []
            self._running = False
            logger.info("Monitoring service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring service: {str(e)}")
            raise
    
    async def _health_check_loop(self) -> None:
        """Run periodic health checks."""
        while True:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Perform health checks
                health_status = await self._check_health()
                
                # Track health check results
                duration = asyncio.get_event_loop().time() - start_time
                for component, status in health_status.items():
                    track_health_check(
                        component=component,
                        status=1.0 if status["healthy"] else 0.0,
                        duration=duration
                    )
                
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
    
    async def _metric_collection_loop(self) -> None:
        """Run periodic metric collection."""
        while True:
            try:
                # Collect and report metrics
                await self._collect_metrics()
                
                await asyncio.sleep(settings.METRIC_COLLECTION_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metric collection failed: {str(e)}")
                await asyncio.sleep(settings.METRIC_COLLECTION_INTERVAL)
    
    async def _check_health(self) -> Dict[str, Any]:
        """
        Check the health of all monitored components.
        
        Returns:
            Dict[str, Any]: Health status of all components
        """
        health_status = {}
        
        try:
            # Check database connections
            from ..database import db_pool
            
            # Check PostgreSQL
            try:
                async with db_pool.postgres_connection() as conn:
                    await conn.execute("SELECT 1")
                health_status["postgres"] = {"healthy": True}
            except Exception as e:
                health_status["postgres"] = {
                    "healthy": False,
                    "error": str(e)
                }
            
            # Check Redis
            try:
                redis = await db_pool.redis_connection()
                await redis.ping()
                health_status["redis"] = {"healthy": True}
            except Exception as e:
                health_status["redis"] = {
                    "healthy": False,
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status["status"] = {
                "healthy": False,
                "error": str(e)
            }
        
        return health_status
    
    async def _collect_metrics(self) -> None:
        """Collect and report metrics."""
        try:
            # Example: Collect database metrics
            from ..database import db_pool
            
            async with db_pool.postgres_connection() as conn:
                # Get sync operation counts
                sync_counts = await conn.fetch("""
                    SELECT status, COUNT(*) as count
                    FROM data_syncs
                    WHERE created_at >= NOW() - INTERVAL '5 minutes'
                    GROUP BY status
                """)
                
                for record in sync_counts:
                    track_sync_operation(
                        source_type="all",
                        status=record["status"],
                        count=record["count"]
                    )
                
                # Get average sync duration
                sync_duration = await conn.fetchval("""
                    SELECT AVG(EXTRACT(EPOCH FROM (end_time - created_at)))
                    FROM data_syncs
                    WHERE end_time IS NOT NULL
                    AND created_at >= NOW() - INTERVAL '5 minutes'
                """)
                
                if sync_duration:
                    track_sync_duration("all", sync_duration)
                
                # Get recovery metrics
                recovery_metrics = await conn.fetch("""
                    SELECT 
                        src.type,
                        src.name,
                        src.source_id,
                        COUNT(*) as total,
                        SUM(CASE WHEN ds.status = 'recovered' THEN 1 ELSE 0 END) as successes,
                        MIN(ds.created_at) as first_sync,
                        MAX(ds.created_at) as last_sync
                    FROM data_syncs ds
                    JOIN data_sources src ON ds.source_id = src.source_id
                    WHERE ds.created_at >= NOW() - INTERVAL '5 minutes'
                    GROUP BY src.type, src.name, src.source_id
                """)
                
                for record in recovery_metrics:
                    source_type = record["type"]
                    track_sync_recovery_attempt(source_type)
                    
                    if record["successes"] > 0:
                        track_sync_recovery_success(source_type)
                    
                    if record["duration"]:
                        track_sync_recovery_duration(source_type, record["duration"])
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}")

# Global monitoring service instance
monitoring_service = MonitoringService()

__all__ = ['monitoring_service', 'MonitoringService'] 