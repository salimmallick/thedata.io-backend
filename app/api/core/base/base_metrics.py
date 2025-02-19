"""
Base metrics interface.
"""
from abc import ABC, abstractmethod
from typing import Any

class BaseMetrics(ABC):
    """Base interface for metrics collection."""
    
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
    
    @abstractmethod
    def get_registry(self) -> Any:
        """Get the metrics registry."""
        pass

class NullMetrics(BaseMetrics):
    """Null implementation of metrics that does nothing."""
    
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        pass
    
    def track_request_latency(self, endpoint: str, latency: float) -> None:
        pass
    
    def track_error(self, error_type: str, error_message: str) -> None:
        pass
    
    def track_database_query(self, database: str, query_type: str, latency: float) -> None:
        pass

    def get_registry(self) -> Any:
        """Return None for null implementation."""
        return None 