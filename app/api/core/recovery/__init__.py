"""
Recovery module initialization.
"""

from .manager import RecoveryManager

# Create the singleton instance
recovery_manager = RecoveryManager()

def init_recovery_manager(db_pool=None):
    """Initialize recovery manager with optional database pool."""
    global recovery_manager
    if db_pool:
        recovery_manager.set_db_pool(db_pool)

__all__ = ['recovery_manager', 'RecoveryManager', 'init_recovery_manager'] 