"""
Base storage interface with no external dependencies.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

class BaseStorageManager(ABC):
    """Abstract base class for storage management."""
    
    @abstractmethod
    async def init_pools(self) -> None:
        """Initialize all database pools."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup all database pools."""
        pass
    
    @abstractmethod
    async def get_postgres_conn(self) -> AsyncGenerator[Any, None]:
        """Get a PostgreSQL connection."""
        pass
    
    @abstractmethod
    async def get_clickhouse_client(self) -> AsyncGenerator[Any, None]:
        """Get a ClickHouse client."""
        pass
    
    @abstractmethod
    async def get_questdb_sender(self) -> AsyncGenerator[Any, None]:
        """Get a QuestDB sender."""
        pass
    
    @abstractmethod
    async def get_nats_client(self) -> AsyncGenerator[Any, None]:
        """Get a NATS client."""
        pass
    
    @abstractmethod
    async def get_redis_conn(self) -> AsyncGenerator[Any, None]:
        """Get a Redis connection."""
        pass

class NullStorageManager(BaseStorageManager):
    """Null implementation of storage manager that does nothing."""
    
    async def init_pools(self) -> None:
        pass
    
    async def cleanup(self) -> None:
        pass
    
    async def get_postgres_conn(self) -> AsyncGenerator[Any, None]:
        yield None
    
    async def get_clickhouse_client(self) -> AsyncGenerator[Any, None]:
        yield None
    
    async def get_questdb_sender(self) -> AsyncGenerator[Any, None]:
        yield None
    
    async def get_nats_client(self) -> AsyncGenerator[Any, None]:
        yield None
    
    async def get_redis_conn(self) -> AsyncGenerator[Any, None]:
        yield None 