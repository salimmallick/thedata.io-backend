"""
Database initialization module.
"""
from typing import Dict, Any
import logging
from ..base.base_storage import BaseStorageManager
from ..auth.security import get_password_hash
from ..config import settings

logger = logging.getLogger(__name__)

async def init_database_schema(db_pool: BaseStorageManager) -> None:
    """Initialize database schema and create required tables."""
    async with db_pool.get_postgres_conn() as conn:
        # Create users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                hashed_password VARCHAR(100) NOT NULL,
                full_name VARCHAR(100),
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create organizations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                api_key VARCHAR(255) UNIQUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create audit logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(50) NOT NULL,
                resource_type VARCHAR(50) NOT NULL,
                resource_id VARCHAR(50),
                details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("Database schema initialized successfully")

async def create_default_admin(db_pool: BaseStorageManager) -> None:
    """Create default admin user if it doesn't exist."""
    async with db_pool.get_postgres_conn() as conn:
        # Check if admin exists
        admin = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1",
            'admin'
        )
        
        if not admin:
            # Create default admin user
            hashed_password = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
            await conn.execute("""
                INSERT INTO users (username, hashed_password, full_name, role)
                VALUES ($1, $2, $3, $4)
            """, 'admin', hashed_password, 'Admin User', 'admin')
            logger.info("Created default admin user")
        else:
            logger.info("Default admin user already exists")

async def initialize_databases(db_pool: BaseStorageManager) -> None:
    """Initialize all databases and create required schemas."""
    try:
        # Initialize PostgreSQL schema
        await init_database_schema(db_pool)
        
        # Create default admin user
        await create_default_admin(db_pool)
        
        # Initialize ClickHouse tables
        async with db_pool.get_clickhouse_client() as client:
            client.command("""
                CREATE TABLE IF NOT EXISTS events (
                    timestamp DateTime,
                    event_type String,
                    user_id String,
                    data String
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, event_type)
            """)
        
        # Initialize QuestDB tables
        async with db_pool.get_questdb_sender() as sender:
            # QuestDB tables are created automatically on first insert
            pass
        
        logger.info("All databases initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize databases: {str(e)}")
        raise 