"""
Base metrics functionality.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseMetrics(ABC):
    """Abstract base class for metrics collection."""
    
    @abstractmethod
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        """Track health status of a component."""
        pass
    
    @abstractmethod
    def track_request_latency(self, endpoint: str, latency: float) -> None:
        """Track request latency for an endpoint."""
        pass
    
    @abstractmethod
    def track_error(self, error_type: str, error_message: str) -> None:
        """Track an error occurrence."""
        pass
    
    @abstractmethod
    def track_database_query(self, database: str, query_type: str, latency: float) -> None:
        """Track database query metrics."""
        pass

class NullMetrics(BaseMetrics):
    """Null implementation of metrics that does nothing."""
    
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

# Note: The metrics instance has been moved to instances.py to prevent circular imports 