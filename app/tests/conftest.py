import pytest
import asyncio
import sys
import time
import os
import httpx
import logging
from pathlib import Path
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
import socket
from app.api.main import app
from app.api.core.config import get_settings, Settings
from app.api.core.database import get_postgres_conn, get_clickhouse_client, get_questdb_sender, get_nats_client, init_redis_pool, init_postgres_pool
from app.api.core.redis import redis
from clickhouse_driver import Client
from unittest.mock import AsyncMock, MagicMock, patch
from questdb.ingress import Sender
from nats.aio.client import Client as NATS

# Get settings instance
settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000", "http://app.example.com"]'
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-key"

def pytest_configure(config):
    """Configure test environment"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        if not loop.is_closed():
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

async def init_service(name: str, check_func, timeout: int = 60) -> bool:
    """Initialize a service with timeout and logging"""
    if name in ["Redis", "QuestDB"]:
        logger.warning(f"Skipping {name} initialization")
        return True
        
    logger.info(f"Initializing {name}...")
    start_time = time.time()
    while True:
        try:
            result = await check_func()
            if result:
                logger.info(f"{name} is ready")
                return True
            await asyncio.sleep(1)
        except Exception as e:
            if time.time() - start_time > timeout:
                logger.error(f"{name} failed to initialize: {str(e)}")
                return False
            await asyncio.sleep(1)

async def check_redis():
    """Check Redis connection"""
    return await redis.ping()

async def check_postgres():
    """Check PostgreSQL connection"""
    try:
        async with get_postgres_conn() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"PostgreSQL check failed: {str(e)}")
        return False

@pytest.fixture(scope="session")
async def clickhouse_client():
    """Initialize ClickHouse client for testing."""
    client_params = {
        'host': 'clickhouse-test',
        'port': 9000,
        'database': 'default',
        'user': 'default'
        # No password parameter for no_password authentication
    }
    
    client = Client(**client_params)
    
    try:
        # Test connection with retries
        max_retries = 5
        retry_delay = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Testing ClickHouse connection (attempt {attempt + 1}/{max_retries})...")
                client.execute("SELECT 1")
                logger.info("Connected to ClickHouse successfully")
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All connection attempts failed: {str(e)}")
                    raise
        
        yield client
    except Exception as e:
        logger.error(f"Failed to connect to ClickHouse: {str(e)}")
        raise
    finally:
        logger.info("Cleaning up ClickHouse connection...")
        client.disconnect()
        logger.info("ClickHouse cleanup complete")

async def check_questdb():
    """Check QuestDB connection"""
    try:
        # First check HTTP endpoint
        async with httpx.AsyncClient() as client:
            # Check status endpoint
            status_response = await client.get("http://questdb-test:9000/status")
            if status_response.status_code != 200:
                return False
                
            # Check metrics endpoint to ensure the server is fully initialized
            metrics_response = await client.get("http://questdb-test:9000/metrics")
            if metrics_response.status_code != 200:
                return False
                
        # Then check PostgreSQL wire protocol
        async with get_postgres_conn() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
            
    except Exception as e:
        logger.warning(f"QuestDB check failed: {str(e)}, but continuing anyway")
        return True  # Continue even if check fails for now

@pytest.fixture
async def nats_client() -> AsyncGenerator[NATS, None]:
    """Create a NATS client for testing."""
    nc = NATS()
    try:
        await nc.connect(
            servers=["nats://nats-test:4222"],
            connect_timeout=5.0,
            max_reconnect_attempts=3,
            name="test-client"
        )
        yield nc
    finally:
        try:
            await nc.drain()
            await nc.close()
        except Exception as e:
            logger.error(f"Error during NATS cleanup: {e}")

@pytest.fixture(scope="session", autouse=True)
async def initialize_services(event_loop):
    """Initialize all required services"""
    # Define service health checks with increased timeouts
    services = {
        "Redis": check_redis,
        "PostgreSQL": check_postgres,
        "ClickHouse": check_clickhouse,
        "QuestDB": check_questdb,
        "NATS": check_nats
    }
    
    # Initialize all services with increased timeout
    results = await asyncio.gather(*[
        init_service(name, check_func, timeout=120)
        for name, check_func in services.items()
    ])
    
    if not all(results):
        failed_services = [name for name, result in zip(services.keys(), results) if not result]
        pytest.fail(f"Service initialization failed for: {', '.join(failed_services)}")
    
    yield
    
    # Cleanup
    from app.api.services.pipeline import pipeline_service
    await pipeline_service.stop()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client for making API requests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(autouse=True)
async def setup_test_db():
    """Setup and teardown test database tables."""
    from app.api.core.database import get_postgres_conn, get_clickhouse_client
    
    # Create test tables
    async with get_postgres_conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                api_key VARCHAR(64) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async with get_clickhouse_client() as client:
        client.execute("""
            CREATE TABLE IF NOT EXISTS test_events (
                event_id String,
                timestamp DateTime64(9),
                event_type String,
                event_name String,
                properties String,
                context String
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, event_type)
        """)
    
    yield
    
    # Cleanup
    async with get_postgres_conn() as conn:
        await conn.execute("DROP TABLE IF EXISTS test_organizations")
    
    async with get_clickhouse_client() as client:
        client.execute("DROP TABLE IF EXISTS test_events")

async def check_clickhouse():
    """Check ClickHouse connection"""
    try:
        logger.info("Attempting to connect to ClickHouse...")
        client_params = {
            'host': 'clickhouse-test',
            'port': 9000,
            'database': 'default',
            'user': 'default',
            'settings': {
                'connect_timeout': 10,
                'send_timeout': 5,
                'receive_timeout': 5,
                'max_execution_time': 30
            }
        }
        
        client = Client(**client_params)
        try:
            # Try multiple queries to ensure the server is really ready
            logger.info("Testing ClickHouse connection...")
            result = client.execute("SELECT 1")
            if result[0][0] != 1:
                raise Exception("Unexpected result from SELECT 1")
                
            # Check if we can create a table
            logger.info("Testing table creation...")
            client.execute("""
                CREATE TABLE IF NOT EXISTS test_connection (
                    id UInt32,
                    value String
                ) ENGINE = Memory
            """)
            
            # Try inserting and selecting data
            logger.info("Testing data insertion and selection...")
            client.execute("INSERT INTO test_connection VALUES", [(1, 'test')])
            result = client.execute("SELECT * FROM test_connection")
            if not result or result[0] != (1, 'test'):
                raise Exception("Data verification failed")
                
            # Clean up
            client.execute("DROP TABLE test_connection")
            
            logger.info("ClickHouse connection check passed successfully")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse operation failed: {str(e)}")
            return False
        finally:
            client.disconnect()
            
    except Exception as e:
        logger.error(f"ClickHouse connection failed: {str(e)}")
        return False

@pytest.fixture(autouse=True)
async def mock_database_connections():
    """Mock all database connections for tests."""
    # Mock Redis
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.__aenter__.return_value = redis_mock
    redis_mock.__aexit__.return_value = None
    
    # Mock PostgreSQL pool
    postgres_pool_mock = AsyncMock()
    postgres_conn_mock = AsyncMock()
    postgres_pool_mock.acquire.return_value = postgres_conn_mock
    postgres_conn_mock.__aenter__.return_value = postgres_conn_mock
    postgres_conn_mock.__aexit__.return_value = None
    
    # Mock ClickHouse
    clickhouse_mock = AsyncMock()
    clickhouse_mock.execute.return_value = [[1]]
    clickhouse_mock.__aenter__.return_value = clickhouse_mock
    clickhouse_mock.__aexit__.return_value = None
    
    # Mock QuestDB
    questdb_mock = AsyncMock()
    questdb_mock.table.return_value = questdb_mock
    questdb_mock.symbol.return_value = questdb_mock
    questdb_mock.at.return_value = questdb_mock
    questdb_mock.float.return_value = questdb_mock
    questdb_mock.flush.return_value = None
    questdb_mock.__aenter__.return_value = questdb_mock
    questdb_mock.__aexit__.return_value = None
    
    # Mock NATS
    nats_mock = AsyncMock()
    nats_mock.connect.return_value = nats_mock
    nats_mock.subscribe.return_value = AsyncMock()
    nats_mock.publish.return_value = None
    nats_mock.drain.return_value = None
    nats_mock.close.return_value = None
    
    with patch('app.api.core.database.Redis', return_value=redis_mock) as redis_patch, \
         patch('app.api.core.database.asyncpg.create_pool', return_value=postgres_pool_mock) as postgres_patch, \
         patch('app.api.core.database.ClickHouseClient', return_value=clickhouse_mock) as clickhouse_patch, \
         patch('app.api.core.database.Sender', return_value=questdb_mock) as questdb_patch, \
         patch('app.api.core.database.nats.connect', return_value=nats_mock) as nats_patch:
        
        yield {
            'redis': redis_mock,
            'postgres': postgres_pool_mock,
            'clickhouse': clickhouse_mock,
            'questdb': questdb_mock,
            'nats': nats_mock
        }

@pytest.fixture
def settings() -> Settings:
    """Get test settings."""
    return Settings()