from typing import Callable, Any, Optional, Dict
import asyncio
import time
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Service considered down
    HALF_OPEN = "half_open"  # Testing if service is back

class CircuitBreaker:
    """Circuit breaker for handling service failures"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_timeout = half_open_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                # Try recovery
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit {self.name} entering half-open state")
            else:
                raise CircuitBreakerError(f"Circuit {self.name} is OPEN")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset circuit
            self._handle_success()
            return result
            
        except Exception as e:
            # Handle failure
            self._handle_failure()
            raise
    
    def _handle_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.last_success_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit {self.name} recovered and CLOSED")
    
    def _handle_failure(self):
        """Handle execution failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} OPENED after {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} returned to OPEN state after failed recovery")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time,
            "last_success": self.last_success_time
        }

class CircuitBreakerError(Exception):
    """Raised when circuit breaker prevents execution"""
    pass

# Create circuit breakers for different services
circuit_breakers = {
    "postgres": CircuitBreaker("postgres"),
    "clickhouse": CircuitBreaker("clickhouse"),
    "questdb": CircuitBreaker("questdb"),
    "redis": CircuitBreaker("redis"),
    "nats": CircuitBreaker("nats")
} 