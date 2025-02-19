"""
Module for storing shared monitoring instances.
This module helps prevent circular imports by providing a central location for shared instances.
"""

from .base_metrics import BaseMetrics, NullMetrics

class NullMetrics(BaseMetrics):
    """Null implementation of metrics collection for initialization"""
    
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        """Do nothing implementation of health tracking."""
        pass
    
    def track_request_latency(self, endpoint: str, latency: float) -> None:
        """Do nothing implementation of latency tracking."""
        pass
    
    def track_error(self, error_type: str, error_message: str) -> None:
        """Do nothing implementation of error tracking."""
        pass
    
    def track_database_query(self, database: str, query_type: str, latency: float) -> None:
        """Do nothing implementation of query tracking."""
        pass

# Global metrics instance that starts as NullMetrics
metrics = NullMetrics()

def init_metrics(metrics_instance):
    """Initialize metrics with a real instance."""
    global metrics
    metrics = metrics_instance 