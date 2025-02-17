"""Database pool manager module."""

import asyncio
import logging
from typing import AsyncGenerator, Optional
import clickhouse_connect
from clickhouse_connect.driver.client import Client
import psycopg
from psycopg.rows import dict_row
from nats.aio.client import Client as NATS
from questdb.ingress import Sender
from ..config import settings
from ..monitoring.base_metrics import metrics

logger = logging.getLogger(__name__)

class DatabasePoolManager:
    """Manages database connection pools for various databases"""
    
    def __init__(self):
        self._postgres_pool = None
        self._clickhouse_client = None
        self._questdb_sender = None
        self._nats_client = None
        
    async def init_pools(self):
        """Initialize all database connection pools"""
        try:
            # Initialize PostgreSQL pool
            self._postgres_pool = await psycopg.AsyncConnection.connect(
                settings.POSTGRES_DSN,
                autocommit=True,
                row_factory=dict_row
            )
            metrics.track_db_connection_count("postgres", 1)
            
            # Initialize ClickHouse client
            self._clickhouse_client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD
            )
            metrics.track_db_connection_count("clickhouse", 1)
            
            # Initialize QuestDB sender
            self._questdb_sender = Sender(settings.QUESTDB_HOST, settings.QUESTDB_PORT)
            
            # Initialize NATS client with authentication
            server_url = settings.NATS_URL
            token = None
            if '@' in server_url:
                # Parse URL to extract token
                parts = server_url.split('@')
                if len(parts) == 2:
                    token = parts[0].split('//')[1]
                    # Update server URL without token
                    server_url = f"nats://{parts[1]}"
            
            options = {
                "servers": [server_url],
                "connect_timeout": 5.0,
                "max_reconnect_attempts": 3,
                "reconnect_time_wait": 1.0,
            }
            
            if token:
                options["token"] = token
                logger.info("Using token authentication for NATS connection")
            
            self._nats_client = await NATS().connect(**options)
            metrics.track_component_health("nats", True)
            
            logger.info("All database pools initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing database pools: {e}")
            metrics.track_component_health("database_pool", False)
            raise
    
    async def cleanup(self):
        """Cleanup all database connections"""
        try:
            if self._postgres_pool:
                await self._postgres_pool.close()
                self._postgres_pool = None
            
            if self._clickhouse_client:
                self._clickhouse_client.close()
                self._clickhouse_client = None
            
            if self._questdb_sender:
                self._questdb_sender.close()
                self._questdb_sender = None
            
            if self._nats_client:
                await self._nats_client.drain()
                self._nats_client = None
            
            logger.info("All database connections cleaned up")
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            raise
    
    @property
    def postgres(self):
        """Get PostgreSQL connection"""
        return self._postgres_pool
    
    @property
    def clickhouse(self):
        """Get ClickHouse client"""
        return self._clickhouse_client
    
    @property
    def questdb(self):
        """Get QuestDB sender"""
        return self._questdb_sender
    
    @property
    def nats(self):
        """Get NATS client"""
        return self._nats_client
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.init_pools()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def postgres_connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get a PostgreSQL connection from the pool"""
        try:
            if not self._postgres_pool or self._postgres_pool.closed:
                await self.init_pools()
            yield self._postgres_pool
        except Exception as e:
            logger.error(f"Error getting PostgreSQL connection: {str(e)}")
            raise
    
    async def clickhouse_connection(self) -> AsyncGenerator[Client, None]:
        """Get a ClickHouse connection"""
        try:
            if not self._clickhouse_client:
                await self.init_pools()
            yield self._clickhouse_client
        except Exception as e:
            logger.error(f"Error getting ClickHouse connection: {str(e)}")
            raise
    
    async def questdb_connection(self) -> AsyncGenerator[Sender, None]:
        """Get a QuestDB connection"""
        try:
            if not self._questdb_sender:
                await self.init_pools()
            yield self._questdb_sender
        except Exception as e:
            logger.error(f"Error getting QuestDB connection: {str(e)}")
            raise
    
    async def nats_connection(self) -> AsyncGenerator[NATS, None]:
        """Get a NATS connection"""
        try:
            if not self._nats_client or not self._nats_client.is_connected:
                await self.init_pools()
            yield self._nats_client
        except Exception as e:
            logger.error(f"Error getting NATS connection: {str(e)}")
            raise 