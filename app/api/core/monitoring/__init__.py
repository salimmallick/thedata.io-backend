"""
Monitoring module initialization.
"""
from typing import Optional
import logging
from .health import HealthChecker
from .metrics import PrometheusMetrics
from .tracing import tracer
from .resource_tracking import ResourceTracker, resource_tracker

logger = logging.getLogger(__name__)

# Global instances
health_checker = HealthChecker()
metrics = None

async def init_monitoring(db_pool=None):
    """
    Initialize monitoring with dependencies.
    
    Args:
        db_pool: Optional database pool instance
        
    Raises:
        ValueError: If initialization fails
    """
    global health_checker, metrics
    
    try:
        # Initialize health checker with database pool
        if db_pool is not None:
            health_checker.initialize(db_pool)
            logger.info("Health checker initialized with database pool")
        
        # Initialize resource tracker
        await resource_tracker.start_tracking()
        logger.info("Resource tracker initialized and started")
        
        logger.info("Monitoring initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring: {str(e)}")
        raise ValueError(f"Failed to initialize monitoring: {str(e)}")

__all__ = ['init_monitoring', 'health_checker', 'metrics'] 