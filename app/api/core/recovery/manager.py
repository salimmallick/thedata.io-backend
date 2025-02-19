"""
Recovery manager for handling critical operation failures.
"""
from typing import Dict, Any, Optional, Callable, Awaitable
import logging
import asyncio
from datetime import datetime
from ..monitoring.instances import metrics
from ..logging.logger import logger

class RecoveryManager:
    """Manages recovery procedures for critical operations."""
    
    def __init__(self):
        """Initialize recovery manager."""
        self._recovery_procedures: Dict[str, Callable] = {}
        self._recovery_states: Dict[str, Dict[str, Any]] = {}
        self._max_retries = 3
        self._backoff_base = 2.0
        self._db_pool = None
    
    def set_db_pool(self, db_pool):
        """Set the database pool instance."""
        self._db_pool = db_pool
    
    async def register_recovery_procedure(
        self,
        operation: str,
        procedure: Callable[..., Awaitable[Any]]
    ) -> None:
        """Register a recovery procedure for an operation."""
        self._recovery_procedures[operation] = procedure
        self._recovery_states[operation] = {
            "last_failure": None,
            "failure_count": 0,
            "last_recovery": None,
            "is_recovering": False
        }
        logger.info(f"Registered recovery procedure for {operation}")
    
    async def handle_failure(
        self,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Handle operation failure and attempt recovery."""
        if operation not in self._recovery_procedures:
            logger.error(f"No recovery procedure registered for {operation}")
            return False
            
        state = self._recovery_states[operation]
        state["last_failure"] = datetime.utcnow()
        state["failure_count"] += 1
        
        if state["failure_count"] > self._max_retries:
            logger.error(f"Max retries exceeded for {operation}")
            return False
            
        try:
            await self.execute_recovery(operation, context)
            return True
        except Exception as e:
            logger.error(f"Recovery failed for {operation}: {str(e)}")
            return False
    
    async def execute_recovery(
        self,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Execute recovery procedure for an operation."""
        if operation not in self._recovery_procedures:
            logger.error(f"No recovery procedure registered for {operation}")
            return
            
        state = self._recovery_states[operation]
        if state["is_recovering"]:
            logger.warning(f"Recovery already in progress for {operation}")
            return
            
        state["is_recovering"] = True
        try:
            procedure = self._recovery_procedures[operation]
            await procedure(context or {})
            state["last_recovery"] = datetime.utcnow()
            state["failure_count"] = 0
            logger.info(f"Recovery successful for {operation}")
        except Exception as e:
            logger.error(f"Recovery failed for {operation}: {str(e)}")
            raise
        finally:
            state["is_recovering"] = False
    
    async def get_recovery_status(self, operation: str) -> Dict[str, Any]:
        """Get recovery status for an operation."""
        if operation not in self._recovery_states:
            raise ValueError(f"No recovery state for {operation}")
        return self._recovery_states[operation]
    
    async def cleanup(self) -> None:
        """Clean up recovery manager resources."""
        self._recovery_procedures.clear()
        self._recovery_states.clear()
        self._db_pool = None

# Create global recovery manager instance
recovery_manager = RecoveryManager()

__all__ = ['recovery_manager', 'RecoveryManager'] 