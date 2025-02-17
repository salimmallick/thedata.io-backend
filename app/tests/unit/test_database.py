import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.api.core.database import (
    init_redis_pool,
    init_postgres_pool,
    get_clickhouse_client,
    get_questdb_sender,
    get_nats_client,
    init_db
)
from app.api.core.config import settings
import tenacity

@pytest.mark.asyncio
async def test_redis_pool_initialization():
    """Test Redis pool initialization."""
    # Mock Redis pool
    mock_pool = AsyncMock()
    mock_pool.ping = AsyncMock(return_value=True)

    with patch('app.api.core.database.Redis.from_url', return_value=mock_pool):
        # Initialize Redis pool
        pool = await init_redis_pool()
        
        # Verify pool was initialized
        assert pool is not None
        assert pool == mock_pool
        
        # Verify ping was called
        mock_pool.ping.assert_called_once()

@pytest.mark.asyncio
async def test_postgres_pool_initialization():
    """Test PostgreSQL pool initialization."""
    # Mock PostgreSQL pool and connection
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    
    # Setup mock connection
    mock_conn.execute = AsyncMock(return_value=None)
    
    # Setup pool acquire context manager
    class MockAcquireContextManager:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
    
    # Setup pool.acquire to return our context manager
    mock_pool.acquire = MagicMock(return_value=MockAcquireContextManager())

    async def mock_create_pool(*args, **kwargs):
        return mock_pool

    with patch('app.api.core.database.asyncpg.create_pool', side_effect=mock_create_pool):
        # Initialize PostgreSQL pool
        pool = await init_postgres_pool()
        
        # Verify pool was initialized
        assert pool is not None
        assert pool == mock_pool
        
        # Verify connection was tested
        mock_pool.acquire.assert_called_once()
        mock_conn.execute.assert_called_once_with('SELECT 1')

@pytest.mark.asyncio
async def test_clickhouse_client():
    """Test ClickHouse client creation."""
    with patch('app.api.core.database.ClickHouseClient') as mock_clickhouse:
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.execute.return_value = [[1]]
        mock_clickhouse.return_value = mock_instance

        # Test client creation
        async with get_clickhouse_client() as client:
            assert client is mock_instance
            mock_instance.execute.assert_called_once_with('SELECT 1')

@pytest.mark.asyncio
async def test_questdb_sender():
    """Test QuestDB sender creation."""
    with patch('app.api.core.database.Sender') as mock_sender:
        # Setup mock
        mock_instance = MagicMock()
        mock_sender.return_value = mock_instance

        # Test sender creation
        async with get_questdb_sender() as sender:
            assert sender is mock_instance

@pytest.mark.asyncio
async def test_nats_client():
    """Test NATS client creation."""
    with patch('nats.connect') as mock_connect:
        # Setup mock
        mock_instance = AsyncMock()
        mock_connect.return_value = mock_instance

        # Test client creation
        async with get_nats_client() as client:
            assert client == mock_instance
            assert mock_connect.called

@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initialization."""
    with patch('app.api.core.database.init_redis_pool') as mock_redis_init, \
         patch('app.api.core.database.init_postgres_pool') as mock_postgres_init:
        # Setup mocks
        mock_redis_init.return_value = None
        mock_postgres_init.return_value = None

        # Test initialization
        await init_db()
        mock_redis_init.assert_called_once()
        mock_postgres_init.assert_called_once()

@pytest.mark.asyncio
async def test_connection_error_handling():
    """Test database connection error handling."""
    # Mock Redis error
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=ConnectionError("Connection failed"))

    with patch('app.api.core.database.Redis.from_url', return_value=mock_redis), \
         pytest.raises(tenacity.RetryError):
        await init_redis_pool()

    # Mock PostgreSQL error
    async def mock_create_pool(*args, **kwargs):
        raise ConnectionError("Connection failed")

    with patch('app.api.core.database.asyncpg.create_pool', new=mock_create_pool), \
         pytest.raises(tenacity.RetryError):
        await init_postgres_pool() 