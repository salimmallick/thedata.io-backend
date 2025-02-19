"""
Database error definitions.
"""
from typing import Optional
import asyncpg
from redis.exceptions import RedisError
from nats.aio.errors import ErrConnectionClosed, ErrTimeout
from clickhouse_connect.driver.exceptions import ClickHouseError
from questdb.ingress import IngressError

class DatabaseError(Exception):
    """Base class for database errors."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

class ConnectionError(DatabaseError):
    """Raised when a database connection cannot be established."""
    pass

class PoolError(DatabaseError):
    """Raised when there's an error with the connection pool."""
    pass

class QueryError(DatabaseError):
    """Raised when a database query fails."""
    pass

class TransactionError(DatabaseError):
    """Raised when a database transaction fails."""
    pass

def wrap_database_error(error: Exception) -> DatabaseError:
    """Convert various database errors to our custom DatabaseError."""
    if isinstance(error, asyncpg.PostgresError):
        return QueryError(f"PostgreSQL error: {str(error)}", error)
    elif isinstance(error, RedisError):
        return ConnectionError(f"Redis error: {str(error)}", error)
    elif isinstance(error, (ErrConnectionClosed, ErrTimeout)):
        return ConnectionError(f"NATS error: {str(error)}", error)
    elif isinstance(error, ClickHouseError):
        return QueryError(f"ClickHouse error: {str(error)}", error)
    elif isinstance(error, IngressError):
        return ConnectionError(f"QuestDB error: {str(error)}", error)
    else:
        return DatabaseError(f"Unknown database error: {str(error)}", error) 