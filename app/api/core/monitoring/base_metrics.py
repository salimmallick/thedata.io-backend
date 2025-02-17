from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseMetrics(ABC):
    """Base interface for metrics collection"""
    
    @abstractmethod
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        """Track health status of a component"""
        pass
    
    @abstractmethod
    def track_db_connection_count(self, database: str, count: int) -> None:
        """Track number of database connections"""
        pass
    
    @abstractmethod
    def track_query_duration(self, database: str, operation: str, duration: float) -> None:
        """Track duration of database queries"""
        pass

    @abstractmethod
    def track_error(self, error_type: str) -> None:
        """Track error occurrence"""
        pass

    @abstractmethod
    def track_cache_miss(self, cache: str) -> None:
        """Track cache miss"""
        pass

    @abstractmethod
    def track_cache_hit(self, cache: str) -> None:
        """Track cache hit"""
        pass

    @abstractmethod
    def track_rate_limit_hit(self, tier: str) -> None:
        """Track rate limit hit"""
        pass

    @abstractmethod
    def track_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """Track HTTP request"""
        pass

# Null implementation for use during initialization
class NullMetrics(BaseMetrics):
    """Null implementation of metrics that does nothing"""
    
    def track_component_health(self, component: str, is_healthy: bool) -> None:
        pass
    
    def track_db_connection_count(self, database: str, count: int) -> None:
        pass
    
    def track_query_duration(self, database: str, operation: str, duration: float) -> None:
        pass

    def track_error(self, error_type: str) -> None:
        pass

    def track_cache_miss(self, cache: str) -> None:
        pass

    def track_cache_hit(self, cache: str) -> None:
        pass

    def track_rate_limit_hit(self, tier: str) -> None:
        pass

    def track_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        pass

# Global metrics instance that starts as NullMetrics
metrics = NullMetrics() 