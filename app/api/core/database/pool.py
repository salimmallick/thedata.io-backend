"""
Database connection pool management with integrated recovery procedures.
"""
from typing import AsyncGenerator, Dict, Any, Optional
from contextlib import asynccontextmanager
import asyncpg
import redis.asyncio as redis
from clickhouse_connect.driver.client import Client
from questdb.ingress import Sender
import nats
import logging

from ..config.settings import settings
from .error_handling import with_database_retry
from .errors import DatabaseError, ConnectionError
from ..logging.logger import logger

logger = logging.getLogger(__name__)

class DatabasePool:
    """Manages database connection pools with integrated recovery."""
    
    def __init__(self):
        """Initialize database pool manager."""
        self._postgres_pool: Optional[asyncpg.Pool] = None
        self._redis_pool: Optional[redis.Redis] = None
        self._initialized = False
        self._recovery_manager = None
    
    def set_recovery_manager(self, recovery_manager):
        """Set the recovery manager instance."""
        self._recovery_manager = recovery_manager
    
    @with_database_retry()
    async def _init_postgres_pool(self) -> None:
        """Initialize PostgreSQL connection pool with recovery integration."""
        try:
            if self._postgres_pool:
                await self._postgres_pool.close()
            
            self._postgres_pool = await asyncpg.create_pool(
                dsn=settings.POSTGRES_DSN,
                min_size=settings.POSTGRES_MIN_POOL_SIZE,
                max_size=settings.POSTGRES_MAX_POOL_SIZE
            )
            logger.info("PostgreSQL connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {str(e)}")
            # Trigger recovery procedure if recovery manager is set
            if self._recovery_manager:
                await self._recovery_manager.execute_recovery(
                    "postgres_connection",
                    context={"error": str(e)}
                )
            raise
    
    @with_database_retry()
    async def _init_redis_pool(self) -> None:
        """Initialize Redis connection pool with recovery integration."""
        try:
            if self._redis_pool:
                await self._redis_pool.close()
            
            self._redis_pool = redis.Redis.from_url(
                settings.REDIS_DSN,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {str(e)}")
            # Trigger recovery procedure if recovery manager is set
            if self._recovery_manager:
                await self._recovery_manager.execute_recovery(
                    "redis_connection",
                    context={"error": str(e)}
                )
            raise
    
    async def init_pools(self) -> None:
        """Initialize all database connection pools."""
        await self._init_postgres_pool()
        await self._init_redis_pool()
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Cleanup all database pools."""
        try:
            if self._postgres_pool:
                await self._postgres_pool.close()
            if self._redis_pool:
                await self._redis_pool.close()
            self._initialized = False
            logger.info("All database pools cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up database pools: {str(e)}")
            raise
    
    @asynccontextmanager
    async def postgres_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a PostgreSQL connection with recovery handling."""
        if not self._initialized:
            await self.init_pools()
        
        if not self._postgres_pool:
            await self._init_postgres_pool()
        
        async with self._postgres_pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                logger.error(f"PostgreSQL operation failed: {str(e)}")
                # Trigger recovery procedure if recovery manager is set
                if self._recovery_manager:
                    try:
                        await self._recovery_manager.execute_recovery(
                            "postgres_connection",
                            context={"error": str(e)}
                        )
                    except Exception as recovery_error:
                        logger.error(f"Recovery failed: {str(recovery_error)}")
                raise DatabaseError(f"Database operation failed: {str(e)}")
    
    @asynccontextmanager
    async def clickhouse_connection(self) -> AsyncGenerator[Client, None]:
        """Get a ClickHouse client."""
        client = Client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB
        )
        try:
            yield client
        finally:
            client.close()
    
    @asynccontextmanager
    async def questdb_connection(self) -> AsyncGenerator[Sender, None]:
        """Get a QuestDB sender."""
        sender = Sender(settings.QUESTDB_HOST, settings.QUESTDB_PORT)
        try:
            await sender.connect()
            yield sender
        finally:
            await sender.close()
    
    @asynccontextmanager
    async def nats_connection(self) -> AsyncGenerator[nats.NATS, None]:
        """Get a NATS client."""
        nc = await nats.connect(settings.NATS_URL)
        try:
            yield nc
        finally:
            await nc.close()
    
    @with_database_retry()
    async def redis_connection(self) -> redis.Redis:
        """Get a Redis connection with recovery handling."""
        if not self._initialized:
            await self.init_pools()
            
        if not self._redis_pool:
            await self._init_redis_pool()
        
        try:
            # Verify connection is alive
            await self._redis_pool.ping()
            return self._redis_pool
        except Exception as e:
            logger.error(f"Failed to acquire Redis connection: {str(e)}")
            # Trigger recovery procedure if recovery manager is set
            if self._recovery_manager:
                try:
                    await self._recovery_manager.execute_recovery(
                        "redis_connection",
                        context={"error": str(e)}
                    )
                except Exception as recovery_error:
                    logger.error(f"Recovery failed: {str(recovery_error)}")
            raise DatabaseError(f"Redis operation failed: {str(e)}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Check health of all database connections."""
        health = {
            "postgres": False,
            "clickhouse": False,
            "questdb": False,
            "nats": False,
            "redis": False
        }
        
        try:
            async with self.postgres_connection() as conn:
                await conn.execute("SELECT 1")
                health["postgres"] = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
        
        try:
            async with self.clickhouse_connection() as client:
                client.command("SELECT 1")
                health["clickhouse"] = True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {str(e)}")
        
        try:
            async with self.questdb_connection() as sender:
                await sender.ping()
                health["questdb"] = True
        except Exception as e:
            logger.error(f"QuestDB health check failed: {str(e)}")
        
        try:
            async with self.nats_connection() as nc:
                await nc.ping()
                health["nats"] = True
        except Exception as e:
            logger.error(f"NATS health check failed: {str(e)}")
        
        try:
            redis_conn = await self.redis_connection()
            await redis_conn.ping()
            health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
        
        health["status"] = all(health.values())
        return health

# Global instance
db_pool = DatabasePool()

__all__ = ['db_pool'] 