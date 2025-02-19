"""
Database error handling utilities.
"""
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

import asyncpg
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .errors import DatabaseError, ConnectionError, PoolError
from ..logging.logger import logger

T = TypeVar("T")

def with_database_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that adds retry logic for database operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries in seconds
        max_wait: Maximum wait time between retries in seconds
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=min_wait, max=max_wait),
            retry=retry_if_exception_type(
                (asyncpg.exceptions.ConnectionDoesNotExistError,
                 asyncpg.exceptions.InterfaceError,
                 asyncpg.exceptions.TooManyConnectionsError,
                 ConnectionError,
                 PoolError)
            ),
            reraise=True
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Database operation failed: {str(e)}")
                raise

        return wrapper
    return decorator 