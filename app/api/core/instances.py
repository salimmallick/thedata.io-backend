"""
Central instance management module.
"""
from typing import Optional

# Initialize instances with null implementations
db_pool = None
metrics = None
health_checker = None

def init_db_pool(pool_instance):
    """Initialize database pool instance."""
    global db_pool
    db_pool = pool_instance

def init_monitoring_instances(
    metrics_instance = None,
    health_checker_instance = None
) -> None:
    """Initialize monitoring instances."""
    global metrics, health_checker
    
    if metrics_instance is not None:
        metrics = metrics_instance
    
    if health_checker_instance is not None:
        health_checker = health_checker_instance

__all__ = ['db_pool', 'metrics', 'health_checker', 'init_monitoring_instances', 'init_db_pool'] 