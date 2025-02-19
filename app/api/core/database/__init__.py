"""
Database management module.
Provides centralized database connection management for all supported databases.
"""

from .pool import DatabasePool
from .errors import DatabaseError

# Create the singleton instance
db_pool = DatabasePool()

def init_db_pool(recovery_manager=None):
    """Initialize database pool with optional recovery manager."""
    global db_pool
    if recovery_manager:
        db_pool.set_recovery_manager(recovery_manager)

__all__ = ['db_pool', 'DatabasePool', 'DatabaseError', 'init_db_pool'] 