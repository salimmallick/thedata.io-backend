"""
Module for storing shared database instances.
This module helps prevent circular imports by providing a central location for shared instances.
"""

from .pool_manager import DatabasePoolManager

# Global database pool instance
db_pool = DatabasePoolManager() 