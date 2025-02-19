"""
Health check router.
"""
from fastapi import APIRouter, HTTPException, status, Response
from ..core.monitoring import health_checker, init_monitoring
from ..core.database import db_pool
from ..core.monitoring.metrics import REGISTRY
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def check_health():
    """Check health of all system components."""
    try:
        # Initialize health checker if not already initialized
        if health_checker is None or not getattr(health_checker, '_initialized', False):
            try:
                init_monitoring(db_pool=db_pool)
            except Exception as e:
                logger.error(f"Failed to initialize health checker: {str(e)}")
                return {
                    "status": "unhealthy",
                    "error": "Failed to initialize health checker",
                    "details": str(e)
                }
        
        # Check health of all components
        health_status = await health_checker.check_all()
        
        # If status is unhealthy, return 503 Service Unavailable
        if health_status["status"] != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status
            )
            
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@router.get("/metrics")
async def metrics():
    """Expose Prometheus metrics"""
    return Response(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )