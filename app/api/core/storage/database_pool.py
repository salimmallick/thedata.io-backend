from typing import Dict, Any, Optional, List
import asyncpg
import aiochclient
import aiohttp
import psycopg2.pool
import clickhouse_driver
from asyncpg.pool import Pool
from clickhouse_driver.client import Client
from app.api.core.config import settings
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from contextlib import asynccontextmanager
from ..monitoring.base_metrics import metrics
import os
import nats

logger = logging.getLogger(__name__)

class DatabasePoolManager:
    """Manager for database connection pools"""
    
    def __init__(self):
        self._postgres_pool: Optional[Pool] = None
        self._clickhouse_clients: List[Client] = []
        self._aiohttp_session = None
        self._nats_client = None
        self._pools_initialized = False
        self._max_pool_size = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
        self._min_pool_size = int(os.getenv("DB_POOL_MIN_SIZE", "5"))
        self._pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self._cleanup_task = None
        self._shutdown = False
    
    async def cleanup(self):
        """Cleanup all database connections"""
        self._shutdown = True
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._postgres_pool:
            await self._postgres_pool.close()
            self._postgres_pool = None
        
        for client in self._clickhouse_clients:
            try:
                client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting ClickHouse client: {e}")
        self._clickhouse_clients = []
        
        if self._aiohttp_session:
            await self._aiohttp_session.close()
            self._aiohttp_session = None
            
        if self._nats_client:
            await self._nats_client.drain()
            await self._nats_client.close()
            self._nats_client = None
        
        self._pools_initialized = False
        logger.info("Database pools cleaned up")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def init_pools(self):
        """Initialize database connection pools"""
        if self._pools_initialized:
            await self.cleanup()
        
        try:
            # Initialize PostgreSQL pool
            self._postgres_pool = await asyncpg.create_pool(
                settings.POSTGRES_URL,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
                command_timeout=self._pool_timeout,
                setup=self._setup_postgres_connection
            )
            
            # Initialize ClickHouse clients
            for _ in range(self._min_pool_size):
                client = Client(
                    host=settings.CLICKHOUSE_HOST,
                    port=settings.CLICKHOUSE_PORT,
                    user=settings.CLICKHOUSE_USER,
                    password=settings.CLICKHOUSE_PASSWORD,
                    settings={'use_numpy': True}
                )
                self._clickhouse_clients.append(client)
            
            # Initialize aiohttp session for async HTTP requests
            self._aiohttp_session = aiohttp.ClientSession()
            
            # Initialize NATS client
            # Extract token from URL if present
            server_url = settings.NATS_URL
            token = None
            if '@' in server_url:
                token = server_url.split('@')[0].split('//')[1]
            
            options = {
                "servers": [settings.NATS_URL],
                "connect_timeout": 5.0,
                "max_reconnect_attempts": 3,
                "reconnect_time_wait": 1.0,
            }
            
            if token:
                options["token"] = token
            
            self._nats_client = await nats.connect(**options)
            
            self._pools_initialized = True
            logger.info("Database pools initialized successfully")
            
            # Start health check and optimization loops
            self._cleanup_task = asyncio.create_task(self._health_check_loop())
            
            # Track initial connection counts
            metrics.track_db_connection_count("postgres", len(self._postgres_pool._holders))
            metrics.track_db_connection_count("clickhouse", len(self._clickhouse_clients))
            
        except Exception as e:
            logger.error(f"Failed to initialize database pools: {str(e)}")
            await self.cleanup()
            raise
    
    async def _health_check_loop(self):
        """Periodically check database connections and clean up stale ones"""
        while not self._shutdown:
            try:
                # Check PostgreSQL pool
                if self._postgres_pool:
                    async with self._postgres_pool.acquire() as conn:
                        await conn.execute('SELECT 1')
                        metrics.track_component_health("postgres", True)
                
                # Check ClickHouse connections
                for client in self._clickhouse_clients:
                    try:
                        client.execute('SELECT 1')
                        metrics.track_component_health("clickhouse", True)
                    except Exception:
                        self._clickhouse_clients.remove(client)
                        client.disconnect()
                        metrics.track_component_health("clickhouse", False)
                
                # Maintain minimum number of ClickHouse clients
                while len(self._clickhouse_clients) < self._min_pool_size:
                    client = Client(
                        host=settings.CLICKHOUSE_HOST,
                        port=settings.CLICKHOUSE_PORT,
                        user=settings.CLICKHOUSE_USER,
                        password=settings.CLICKHOUSE_PASSWORD,
                        settings={'use_numpy': True}
                    )
                    self._clickhouse_clients.append(client)
                    
                # Check NATS connection
                if self._nats_client and not self._nats_client.is_connected:
                    # Extract token from URL if present
                    server_url = settings.NATS_URL
                    token = None
                    if '@' in server_url:
                        token = server_url.split('@')[0].split('//')[1]
                    
                    options = {
                        "servers": [settings.NATS_URL],
                        "connect_timeout": 5.0,
                        "max_reconnect_attempts": 3,
                        "reconnect_time_wait": 1.0,
                    }
                    
                    if token:
                        options["token"] = token
                    
                    self._nats_client = await nats.connect(**options)
                    metrics.track_component_health("nats", True)
                
                # Update connection counts
                metrics.track_db_connection_count("postgres", len(self._postgres_pool._holders))
                metrics.track_db_connection_count("clickhouse", len(self._clickhouse_clients))
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                metrics.track_component_health("database_pool", False)
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _setup_postgres_connection(self, conn):
        """Setup PostgreSQL connection with proper settings"""
        await conn.execute('SET statement_timeout = 30000')  # 30 seconds
        await conn.execute('SET idle_in_transaction_session_timeout = 60000')  # 1 minute
    
    @asynccontextmanager
    async def postgres_connection(self):
        """Get a PostgreSQL connection from the pool"""
        if not self._pools_initialized:
            await self.init_pools()
        
        if not self._postgres_pool:
            raise Exception("PostgreSQL pool not initialized")
        
        start_time = asyncio.get_event_loop().time()
        async with self._postgres_pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                logger.error(f"Error in PostgreSQL connection: {e}")
                metrics.track_component_health("postgres", False)
                raise
            finally:
                duration = asyncio.get_event_loop().time() - start_time
                metrics.track_query_duration("postgres", "query", duration)
    
    @asynccontextmanager
    async def clickhouse_connection(self):
        """Get a ClickHouse connection from the pool"""
        if not self._pools_initialized:
            await self.init_pools()
        
        # Get an available client
        client = None
        for c in self._clickhouse_clients:
            if not c.connected:
                client = c
                break
        
        if client is None and len(self._clickhouse_clients) < self._max_pool_size:
            client = Client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                user=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                settings={'use_numpy': True}
            )
            self._clickhouse_clients.append(client)
        
        if client is None:
            raise Exception("No available ClickHouse connections")
        
        start_time = asyncio.get_event_loop().time()
        try:
            if not client.connected:
                client.connect()
            yield client
        except Exception as e:
            logger.error(f"Error in ClickHouse connection: {e}")
            metrics.track_component_health("clickhouse", False)
            raise
        finally:
            try:
                client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting ClickHouse client: {e}")
            duration = asyncio.get_event_loop().time() - start_time
            metrics.track_query_duration("clickhouse", "query", duration)
                
    @asynccontextmanager
    async def nats_connection(self):
        """Get a NATS connection"""
        if not self._pools_initialized:
            await self.init_pools()
            
        if not self._nats_client or not self._nats_client.is_connected:
            # Extract token from URL if present
            server_url = settings.NATS_URL
            token = None
            if '@' in server_url:
                token = server_url.split('@')[0].split('//')[1]
            
            options = {
                "servers": [settings.NATS_URL],
                "connect_timeout": 5.0,
                "max_reconnect_attempts": 3,
                "reconnect_time_wait": 1.0,
            }
            
            if token:
                options["token"] = token
            
            self._nats_client = await nats.connect(**options)
            
        start_time = asyncio.get_event_loop().time()
        try:
            yield self._nats_client
            metrics.track_component_health("nats", True)
        except Exception as e:
            logger.error(f"Error in NATS connection: {e}")
            metrics.track_component_health("nats", False)
            raise
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            metrics.track_query_duration("nats", "operation", duration)
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.cleanup())
        except Exception:
            pass  # Ignore cleanup errors during deletion

    async def check_pool_health(self) -> Dict[str, Any]:
        """Check health of the database pool"""
        if not self._pools_initialized:
            return {"status": "error", "error": "Pools not initialized"}

        try:
            if not self._postgres_pool:
                return {"status": "error", "error": "PostgreSQL pool not initialized"}
                
            async with self._postgres_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                metrics.track_component_health("database_pool", True)
                return {"status": "healthy"}
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            metrics.track_component_health("database_pool", False)
            return {"status": "error", "error": str(e)}

    async def get_pool_stats(self, db: str) -> Dict[str, Any]:
        """Get statistics for a specific database pool"""
        if not self._pools_initialized:
            return {"error": "Pools not initialized"}

        try:
            if db == "postgres":
                if not self._postgres_pool:
                    return {"error": "PostgreSQL pool not initialized"}
                    
                stats = self._postgres_pool.get_stats()
                metrics.track_db_connection_count("postgres", stats.get("size", 0))
                return {
                    "total_connections": stats.get("size", 0),
                    "used_connections": stats.get("used", 0),
                    "idle_connections": stats.get("idle", 0),
                    "min_size": self._min_pool_size,
                    "max_size": self._max_pool_size
                }
                
            elif db == "clickhouse":
                if not self._clickhouse_clients:
                    return {"error": "ClickHouse pool not initialized"}
                    
                metrics.track_db_connection_count("clickhouse", len(self._clickhouse_clients))
                return {
                    "pool_size": len(self._clickhouse_clients),
                    "min_size": self._min_pool_size,
                    "max_size": self._max_pool_size
                }
                
            return {"error": f"Unknown database type: {db}"}
                
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {"error": str(e)}

# Global instance
db_pool = DatabasePoolManager()
postgres_pool = db_pool.postgres_connection
init_postgres_pool = db_pool.init_pools 