from typing import Dict, Optional
import asyncio
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
        self._lock = asyncio.Lock()

    async def record_failure(self) -> None:
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            if self.failure_count >= self.failure_threshold:
                self.is_open = True

    async def record_success(self) -> None:
        async with self._lock:
            self.failure_count = 0
            self.is_open = False
            self.last_failure_time = None

    async def can_execute(self) -> bool:
        if not self.is_open:
            return True

        if self.last_failure_time and datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.reset_timeout):
            async with self._lock:
                self.failure_count = 0
                self.is_open = False
                self.last_failure_time = None
            return True

        return False

    async def execute(self, func, *args, **kwargs):
        if not await self.can_execute():
            raise CircuitBreakerError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure()
            raise e

class CircuitBreakerError(Exception):
    pass

# Create circuit breakers for different services
circuit_breakers: Dict[str, CircuitBreaker] = {
    "postgres": CircuitBreaker(),
    "clickhouse": CircuitBreaker(),
    "questdb": CircuitBreaker(),
    "nats": CircuitBreaker(),
    "redis": CircuitBreaker(),
    "materialize": CircuitBreaker(),
} 