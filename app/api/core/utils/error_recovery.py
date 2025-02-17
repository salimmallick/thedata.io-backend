from typing import Dict, Any, Optional, Callable, Awaitable
import asyncio
from datetime import datetime, timedelta
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from ..monitoring.metrics import metrics
from .circuit_breaker import circuit_breakers

logger = logging.getLogger(__name__)

class RecoveryStrategy:
    """Base class for recovery strategies"""
    
    def __init__(self, max_attempts: int = 3, initial_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.attempts = 0
        self.last_attempt = None
        self.success_count = 0
        self.failure_count = 0
    
    async def attempt_recovery(self, error: Exception) -> bool:
        """Attempt to recover from an error"""
        if self.attempts >= self.max_attempts:
            return False
            
        self.attempts += 1
        self.last_attempt = datetime.utcnow()
        
        try:
            await self._execute_recovery(error)
            self.success_count += 1
            return True
        except Exception as e:
            logger.error(f"Recovery attempt failed: {str(e)}")
            self.failure_count += 1
            return False
    
    async def _execute_recovery(self, error: Exception):
        """Execute recovery logic - to be implemented by subclasses"""
        raise NotImplementedError

class DatabaseRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for database errors"""
    
    async def _execute_recovery(self, error: Exception):
        # Check connection pool health
        await self._check_connection_pools()
        
        # Attempt to reconnect if necessary
        if "connection" in str(error).lower():
            await self._attempt_reconnection()
        
        # Clear any stale connections
        await self._clear_stale_connections()
    
    async def _check_connection_pools(self):
        """Check health of connection pools"""
        from .database_pool import db_pool
        await db_pool.check_pool_health("postgres")
        await db_pool.check_pool_health("clickhouse")
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect to databases"""
        from .database_pool import db_pool
        await db_pool.init_pools()
    
    async def _clear_stale_connections(self):
        """Clear stale connections from pools"""
        from .database_pool import db_pool
        await db_pool.cleanup()

class MessageQueueRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for message queue errors"""
    
    async def _execute_recovery(self, error: Exception):
        # Check NATS connection
        await self._check_nats_connection()
        
        # Attempt to recover lost messages
        if "message" in str(error).lower():
            await self._recover_lost_messages()
        
        # Reset stream if necessary
        if "stream" in str(error).lower():
            await self._reset_stream()
    
    async def _check_nats_connection(self):
        """Check NATS connection status"""
        from .database import get_nats_client
        nc = await get_nats_client()
        if not nc.is_connected:
            await nc.reconnect()
    
    async def _recover_lost_messages(self):
        """Attempt to recover lost messages"""
        # Implement message recovery logic
        pass
    
    async def _reset_stream(self):
        """Reset stream if necessary"""
        # Implement stream reset logic
        pass

class ValidationRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for validation errors"""
    
    async def _execute_recovery(self, error: Exception):
        # Check validation components
        await self._check_validation_components()
        
        # Reset validation state if necessary
        if "state" in str(error).lower():
            await self._reset_validation_state()
        
        # Clear validation cache
        await self._clear_validation_cache()
    
    async def _check_validation_components(self):
        """Check validation component health"""
        # Implement validation component check
        pass
    
    async def _reset_validation_state(self):
        """Reset validation state"""
        # Implement validation state reset
        pass
    
    async def _clear_validation_cache(self):
        """Clear validation cache"""
        from .cache import cache_manager
        await cache_manager.invalidate("validation:*")

class RecoveryManager:
    """Manager for error recovery strategies"""
    
    def __init__(self):
        self.strategies = {
            "database": DatabaseRecoveryStrategy(),
            "message_queue": MessageQueueRecoveryStrategy(),
            "validation": ValidationRecoveryStrategy()
        }
        self.recovery_history: Dict[str, List[Dict[str, Any]]] = {}
    
    async def attempt_recovery(
        self,
        error_type: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Attempt to recover from an error"""
        strategy = self.strategies.get(error_type)
        if not strategy:
            logger.error(f"No recovery strategy found for error type: {error_type}")
            return False
        
        # Track recovery attempt
        attempt_info = {
            "timestamp": datetime.utcnow(),
            "error": str(error),
            "context": context or {}
        }
        
        if error_type not in self.recovery_history:
            self.recovery_history[error_type] = []
        
        self.recovery_history[error_type].append(attempt_info)
        
        # Attempt recovery
        success = await strategy.attempt_recovery(error)
        
        # Track metrics
        self._track_recovery_metrics(error_type, success)
        
        return success
    
    def _track_recovery_metrics(self, error_type: str, success: bool):
        """Track recovery metrics"""
        metrics.track_error_recovery(
            error_type=error_type,
            success=success
        )
    
    async def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        stats = {}
        for error_type, strategy in self.strategies.items():
            stats[error_type] = {
                "attempts": strategy.attempts,
                "successes": strategy.success_count,
                "failures": strategy.failure_count,
                "last_attempt": strategy.last_attempt,
                "success_rate": (
                    strategy.success_count / strategy.attempts
                    if strategy.attempts > 0 else 0
                )
            }
        return stats
    
    async def cleanup_history(self, older_than: timedelta = timedelta(days=7)):
        """Clean up old recovery history"""
        cutoff = datetime.utcnow() - older_than
        for error_type in self.recovery_history:
            self.recovery_history[error_type] = [
                attempt for attempt in self.recovery_history[error_type]
                if attempt["timestamp"] > cutoff
            ]

# Create global recovery manager
recovery_manager = RecoveryManager() 