from typing import Dict, Any
import asyncio
from ..storage.instances import db_pool
from ..storage.redis import redis
import logging
from .base_metrics import metrics
from fastapi import HTTPException, status
from ..storage.config import settings
from ..monitoring.circuit_breaker import circuit_breakers

logger = logging.getLogger(__name__)

class HealthChecker:
    """Health checker for various components"""
    
    @staticmethod
    async def check_postgres() -> bool:
        """Check PostgreSQL health"""
        try:
            async with db_pool.postgres_connection() as conn:
                await conn.execute("SELECT 1")
                metrics.track_component_health("postgres", True)
                return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
            metrics.track_component_health("postgres", False)
            return False
    
    @staticmethod
    async def check_clickhouse() -> bool:
        """Check ClickHouse health"""
        try:
            async with db_pool.clickhouse_connection() as client:
                client.query("SELECT 1")
                metrics.track_component_health("clickhouse", True)
                return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {str(e)}")
            metrics.track_component_health("clickhouse", False)
            return False
    
    @staticmethod
    async def check_questdb() -> bool:
        """Check QuestDB health"""
        try:
            async with db_pool.questdb_connection() as sender:
                await sender.flush()
                metrics.track_component_health("questdb", True)
                return True
        except Exception as e:
            logger.error(f"QuestDB health check failed: {str(e)}")
            metrics.track_component_health("questdb", False)
            return False
    
    @staticmethod
    async def check_nats() -> bool:
        """Check NATS health"""
        try:
            async with db_pool.nats_connection() as nc:
                if nc.is_connected:
                    metrics.track_component_health("nats", True)
                    return True
                metrics.track_component_health("nats", False)
                return False
        except Exception as e:
            logger.error(f"NATS health check failed: {str(e)}")
            metrics.track_component_health("nats", False)
            return False
    
    @staticmethod
    async def check_all() -> dict:
        """Check health of all components"""
        results = {
            "postgres": await HealthChecker.check_postgres(),
            "clickhouse": await HealthChecker.check_clickhouse(),
            "questdb": await HealthChecker.check_questdb(),
            "nats": await HealthChecker.check_nats()
        }
        return results
    
    @staticmethod
    async def check_health():
        """Check health of all services and raise HTTP exception if all are unhealthy"""
        results = await HealthChecker.check_all()
        if not any(results.values()):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="All services are unhealthy"
            )

# Initialize health checker
health_checker = HealthChecker()

async def _measure_db_latency(db_type: str) -> float:
    """Measure database query latency"""
    start = asyncio.get_event_loop().time()
    
    try:
        if db_type == "postgres":
            async with db_pool.postgres_connection() as conn:
                await conn.fetchval("SELECT 1")
        elif db_type == "clickhouse":
            async with db_pool.clickhouse_connection() as client:
                client.execute("SELECT 1")
        elif db_type == "questdb":
            async with db_pool.postgres_connection() as conn:
                await conn.fetchval("SELECT 1")
    except Exception:
        return -1
    
    duration = asyncio.get_event_loop().time() - start
    metrics.track_query_duration(db_type, "health_check", duration)
    return duration

async def _measure_cache_latency() -> float:
    """Measure Redis operation latency"""
    start = asyncio.get_event_loop().time()
    
    try:
        await redis._redis.ping()
    except Exception:
        return -1
    
    duration = asyncio.get_event_loop().time() - start
    metrics.track_query_duration("redis", "health_check", duration)
    return duration

async def _measure_messaging_latency() -> float:
    """Measure NATS messaging latency"""
    start = asyncio.get_event_loop().time()
    
    try:
        async with db_pool.nats_connection() as nc:
            await nc.ping()
    except Exception:
        return -1
    
    duration = asyncio.get_event_loop().time() - start
    metrics.track_query_duration("nats", "health_check", duration)
    return duration

class HealthCheck:
    @staticmethod
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
            "redis": settings.REDIS_URL,
            "materialize": settings.MATERIALIZE_URL
        }

        for service_name, _ in services.items():
            circuit_breaker = circuit_breakers.get(service_name)
            if circuit_breaker and circuit_breaker.is_open:
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "message": f"Circuit breaker is open for {service_name}"
                }
                health_status["status"] = "degraded"
                metrics.track_component_health(service_name, False)
            else:
                health_status["services"][service_name] = {
                    "status": "healthy"
                }
                metrics.track_component_health(service_name, True)

        if all(service["status"] == "unhealthy" for service in health_status["services"].values()):
            health_status["status"] = "unhealthy"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="All services are unhealthy"
            )

        return health_status 