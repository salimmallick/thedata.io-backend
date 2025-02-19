"""
Base health check interface with no external dependencies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseHealthChecker(ABC):
    """Abstract base class for health checking."""
    
    @abstractmethod
    async def check_postgres(self, db_pool) -> bool:
        """Check PostgreSQL database health."""
        pass

    @abstractmethod
    async def check_clickhouse(self, db_pool) -> bool:
        """Check ClickHouse database health."""
        pass

    @abstractmethod
    async def check_questdb(self, db_pool) -> bool:
        """Check QuestDB health."""
        pass

    @abstractmethod
    async def check_nats(self, db_pool) -> bool:
        """Check NATS health."""
        pass

    @abstractmethod
    async def check_redis(self, db_pool) -> bool:
        """Check Redis health."""
        pass

    @abstractmethod
    async def check_all(self, db_pool) -> Dict[str, Any]:
        """Check health of all components."""
        pass

class NullHealthChecker(BaseHealthChecker):
    """Null implementation of health checker that always returns healthy."""
    
    async def check_postgres(self, db_pool) -> bool:
        return True

    async def check_clickhouse(self, db_pool) -> bool:
        return True

    async def check_questdb(self, db_pool) -> bool:
        return True

    async def check_nats(self, db_pool) -> bool:
        return True

    async def check_redis(self, db_pool) -> bool:
        return True

    async def check_all(self, db_pool) -> Dict[str, Any]:
        return {
            "status": True,
            "postgres": True,
            "clickhouse": True,
            "questdb": True,
            "nats": True,
            "redis": True
        } 