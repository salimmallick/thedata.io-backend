"""
Retry utility module for handling retries with configurable backoff strategies.
"""
from typing import Callable, TypeVar, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
from functools import wraps
from ..monitoring.instances import metrics

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

class RetryState:
    """Tracks the state of retries for a particular operation."""
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempts = 0
        self.last_attempt = None
        self.last_error = None
        self.total_delay = 0.0

    def should_retry(self, error: Exception) -> bool:
        """Determine if another retry should be attempted."""
        self.attempts += 1
        self.last_attempt = datetime.utcnow()
        self.last_error = error

        # Don't retry if we've hit the max attempts
        if self.attempts >= self.config.max_attempts:
            return False

        # Don't retry certain types of errors
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return False

        return True

    def get_delay(self) -> float:
        """Calculate the next retry delay using exponential backoff."""
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** (self.attempts - 1)),
            self.config.max_delay
        )

        if self.config.jitter:
            # Add jitter to prevent thundering herd
            delay = delay * (0.5 + asyncio.get_event_loop().time() % 1)

        self.total_delay += delay
        return delay

def with_retry(
    retry_config: Optional[RetryConfig] = None,
    metric_name: Optional[str] = None
):
    """Decorator for adding retry behavior to async functions."""
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func: Callable[..., T]):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            state = RetryState(retry_config)
            
            while True:
                try:
                    result = await func(*args, **kwargs)
                    
                    # Track successful retry metrics if this wasn't first attempt
                    if state.attempts > 0 and metric_name:
                        metrics.track_retry_success(
                            metric_name,
                            attempts=state.attempts,
                            total_delay=state.total_delay
                        )
                    
                    return result
                
                except Exception as e:
                    if not state.should_retry(e):
                        # Track failed retry metrics
                        if metric_name:
                            metrics.track_retry_failure(
                                metric_name,
                                attempts=state.attempts,
                                total_delay=state.total_delay,
                                error=str(e)
                            )
                        raise

                    delay = state.get_delay()
                    
                    logger.warning(
                        f"Retry attempt {state.attempts} for {func.__name__} "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
                    
                    # Track retry attempt metrics
                    if metric_name:
                        metrics.track_retry_attempt(
                            metric_name,
                            attempt=state.attempts,
                            delay=delay,
                            error=str(e)
                        )
                    
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit breaker for preventing repeated failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, or half-open
        
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failures} failures")
    
    def record_success(self):
        """Record a success and potentially close the circuit."""
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"
    
    def can_execute(self) -> bool:
        """Check if execution should be allowed."""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            # Check if enough time has passed to try half-open
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.reset_timeout:
                    self.state = "half-open"
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False
            
        if self.state == "half-open":
            # Allow limited traffic in half-open state
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            return elapsed >= self.half_open_timeout
            
        return True

def with_circuit_breaker(breaker: CircuitBreaker, fallback: Optional[Callable] = None):
    """Decorator for adding circuit breaker behavior to async functions."""
    def decorator(func: Callable[..., T]):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if not breaker.can_execute():
                if fallback:
                    return await fallback(*args, **kwargs)
                raise Exception("Circuit breaker is open")
                
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
                
        return wrapper
    return decorator 