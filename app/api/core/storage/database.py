from typing import AsyncGenerator, Optional
import asyncpg
from questdb.ingress import Sender, IngressError
import asyncio
from contextlib import asynccontextmanager
from redis.asyncio import Redis
import nats
from app.api.core.config import settings
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from .database_pool import DatabasePoolManager
from .instances import db_pool
from clickhouse_connect.driver.client import Client
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

# Global connection pools
redis_pool: Optional[Redis] = None
db_pool_manager = DatabasePoolManager()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def init_redis_pool() -> Redis:
    """Initialize Redis connection pool."""
    try:
        redis_pool = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        await redis_pool.ping()
        logger.info("Successfully initialized Redis pool")
        return redis_pool
    except Exception as e:
        logger.error(f"Failed to create Redis pool: {str(e)}")
        raise ConnectionError(f"Failed to connect to Redis: {str(e)}")

async def get_redis_conn() -> Redis:
    if redis_pool is None:
        await init_redis_pool()
    return redis_pool

@asynccontextmanager
async def get_postgres_conn() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Get a PostgreSQL connection."""
    async with db_pool.postgres_connection() as conn:
        yield conn

@asynccontextmanager
async def get_clickhouse_client() -> AsyncGenerator[Client, None]:
    """Get a ClickHouse client."""
    async with db_pool.clickhouse_connection() as client:
        yield client

@asynccontextmanager
async def get_questdb_sender() -> AsyncGenerator[Sender, None]:
    """Get a QuestDB sender."""
    async with db_pool.questdb_connection() as sender:
        yield sender

@asynccontextmanager
async def get_nats_client() -> AsyncGenerator[nats.NATS, None]:
    """Get a NATS client."""
    async with db_pool.nats_connection() as client:
        yield client

async def init_db() -> None:
    """Initialize database with required tables and default admin user."""
    await db_pool_manager.init_pools()
    
    async with db_pool_manager.postgres_connection() as conn:
        # Create tables
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                is_active BOOLEAN DEFAULT true,
                is_superuser BOOLEAN DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                api_key VARCHAR(255) UNIQUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Check if admin user exists
        admin_exists = await conn.fetchval(
            'SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)',
            'admin@thedata.io'
        )
        
        if not admin_exists:
            # Create default admin user
            from ..auth.security import get_password_hash
            hashed_password = get_password_hash('admin123')
            await conn.execute('''
                INSERT INTO users (email, hashed_password, full_name, is_superuser)
                VALUES ($1, $2, $3, $4)
            ''', 'admin@thedata.io', hashed_password, 'Admin User', True)
            logger.info("Created default admin user")

    try:
        await init_redis_pool()
        logger.info("Successfully initialized all database connections")
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {str(e)}")
        raise 