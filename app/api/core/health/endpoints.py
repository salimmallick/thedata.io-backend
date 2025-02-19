"""
Health check endpoints with integrated recovery procedures.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..database import db_pool
from ..logging.logger import logger
from ..recovery.manager import recovery_manager

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check the health of all system components with recovery integration.
    
    Returns:
        Dict[str, Any]: Health status of all components
    """
    try:
        health_status = {
            "status": "healthy",
            "components": {}
        }
        
        # Check database connections
        try:
            async with db_pool.postgres_connection() as conn:
                await conn.execute("SELECT 1")
            health_status["components"]["postgres"] = {"status": "healthy"}
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
            health_status["components"]["postgres"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            # Trigger recovery
            await recovery_manager.execute_recovery(
                "postgres_connection",
                context={"error": str(e)}
            )
        
        try:
            redis = await db_pool.redis_connection()
            await redis.ping()
            health_status["components"]["redis"] = {"status": "healthy"}
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            # Trigger recovery
            await recovery_manager.execute_recovery(
                "redis_connection",
                context={"error": str(e)}
            )
        
        # Check recovery manager status
        recovery_status = await recovery_manager.get_status()
        health_status["components"]["recovery"] = {
            "status": "healthy" if recovery_status["healthy"] else "unhealthy",
            "active_recoveries": recovery_status["active_recoveries"],
            "failed_recoveries": recovery_status["failed_recoveries"]
        }
        
        # Update overall status
        if any(component["status"] == "unhealthy" 
               for component in health_status["components"].values()):
            health_status["status"] = "degraded"
        
        logger.info("Health check completed", extra={"status": health_status["status"]})
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

__all__ = ['router'] 