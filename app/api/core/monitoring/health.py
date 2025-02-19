"""
Health check module with metrics integration.
"""
import asyncio
from typing import Dict, Any
from fastapi import HTTPException, status
from ..base.base_health import BaseHealthChecker
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class HealthChecker(BaseHealthChecker):
    """Health checker with metrics integration."""
    
    def __init__(self):
        """Initialize the health checker."""
        self._initialized = False
        self._db_pool = None
    
    def initialize(self, db_pool):
        """Initialize the health checker with dependencies."""
        self._db_pool = db_pool
        self._initialized = True
    
    async def check_postgres(self, db_pool=None) -> Dict[str, Any]:
        """Check PostgreSQL database health."""
        db_pool = db_pool or self._db_pool
        try:
            async with db_pool.postgres_connection() as conn:
                await conn.execute("SELECT 1")
                return {"status": True}
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
            return {"status": False, "error": str(e)}

    async def check_clickhouse(self, db_pool=None) -> Dict[str, Any]:
        """Check ClickHouse database health with metrics."""
        if not self._initialized:
            raise ValueError("Health checker not initialized")
            
        db_pool = db_pool or self._db_pool
        if not db_pool:
            return {"status": False, "error": "Database pool not initialized"}
            
        try:
            # Add ClickHouse health check implementation
            return {"status": True}
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {str(e)}")
            return {"status": False, "error": str(e)}

    async def check_questdb(self, db_pool=None) -> Dict[str, Any]:
        """Check QuestDB health with metrics."""
        if not self._initialized:
            raise ValueError("Health checker not initialized")
            
        db_pool = db_pool or self._db_pool
        if not db_pool:
            return {"status": False, "error": "Database pool not initialized"}
            
        try:
            # Add QuestDB health check implementation
            return {"status": True}
        except Exception as e:
            logger.error(f"QuestDB health check failed: {str(e)}")
            return {"status": False, "error": str(e)}

    async def check_nats(self, db_pool=None) -> Dict[str, Any]:
        """Check NATS health with metrics."""
        if not self._initialized:
            raise ValueError("Health checker not initialized")
            
        db_pool = db_pool or self._db_pool
        if not db_pool:
            return {"status": False, "error": "Database pool not initialized"}
            
        try:
            # Add NATS health check implementation
            return {"status": True}
        except Exception as e:
            logger.error(f"NATS health check failed: {str(e)}")
            return {"status": False, "error": str(e)}

    async def check_redis(self, db_pool=None) -> Dict[str, Any]:
        """Check Redis health."""
        db_pool = db_pool or self._db_pool
        try:
            redis = await db_pool.redis_connection()
            await redis.ping()
            return {"status": True}
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {"status": False, "error": str(e)}

    async def check_all(self, db_pool=None) -> Dict[str, Any]:
        """Check health of all components."""
        db_pool = db_pool or self._db_pool
        if not db_pool:
            return {
                "status": "unhealthy",
                "error": "Database pool not initialized",
                "components": {}
            }
            
        components = {}
        
        # Check core components
        components["postgres"] = await self.check_postgres(db_pool)
        components["redis"] = await self.check_redis(db_pool)
        
        # Determine overall status
        is_healthy = all(component.get("status", False) for component in components.values())
                
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "components": components
        }

# Global instance
health_checker = HealthChecker()

__all__ = ['HealthChecker', 'health_checker']

async def _measure_db_latency(db_type: str) -> float:
    """Measure database query latency"""
    start = asyncio.get_event_loop().time()
    
    try:
        if db_type == "postgres":
            async with self._db_pool.get_postgres_conn() as conn:
                await conn.execute("SELECT 1")
        elif db_type == "clickhouse":
            async with self._db_pool.clickhouse_connection() as client:
                client.execute("SELECT 1")
        elif db_type == "questdb":
            async with self._db_pool.questdb_connection() as session:
                async with session.get(f"http://{settings.QUESTDB_HOST}:{settings.QUESTDB_PORT}/health") as response:
                    if response.status != 200:
                        return -1
    except Exception:
        return -1
    
    duration = asyncio.get_event_loop().time() - start
    if metrics:
        metrics.track_query_duration(db_type, "health_check", duration)
    return duration

async def _measure_messaging_latency() -> float:
    """Measure NATS messaging latency"""
    start = asyncio.get_event_loop().time()
    
    try:
        async with self._db_pool.nats_connection() as nc:
            await nc.ping()
    except Exception:
        return -1
    
    duration = asyncio.get_event_loop().time() - start
    if metrics:
        metrics.track_query_duration("nats", "health_check", duration)
    return duration

def check_health() -> Dict[str, Any]:
    """Check the health of all services."""
    health_status = {
        "status": "healthy",
        "services": {}
    }

    services = {
        "postgres": settings.POSTGRES_URL,
        "clickhouse": settings.CLICKHOUSE_URL,
        "questdb": settings.QUESTDB_URL,
        "nats": settings.NATS_URL,
        "materialize": settings.MATERIALIZE_URL
    }

    for service_name, _ in services.items():
        try:
            if self._db_pool:
                is_healthy = True  # We'll update this with actual checks
                if metrics:
                    metrics.track_component_health(service_name, is_healthy)
                health_status["services"][service_name] = {
                    "status": "healthy" if is_healthy else "unhealthy"
                }
            else:
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "message": "Database pool not initialized"
                }
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["services"][service_name] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health_status["status"] = "degraded"
            if metrics:
                metrics.track_component_health(service_name, False)

    if all(service["status"] == "unhealthy" for service in health_status["services"].values()):
        health_status["status"] = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="All services are unhealthy"
        )

    return health_status 