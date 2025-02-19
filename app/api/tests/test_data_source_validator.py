"""
Tests for data source validator.
"""
import pytest
from datetime import datetime
from ..services.data_source_validator import data_source_validator
from ..models.data_source import (
    DataSourceType,
    DataSourceStatus,
    DataSourceHealth,
    ConnectionConfig
)

@pytest.fixture
def sample_postgresql_config():
    """Sample PostgreSQL configuration."""
    return {
        "connection": {
            "host": "localhost",
            "port": 5432,
            "username": "test_user",
            "password": "test_pass",
            "database": "test_db",
            "ssl_enabled": False,
            "connection_timeout": 5
        }
    }

@pytest.fixture
def sample_mysql_config():
    """Sample MySQL configuration."""
    return {
        "connection": {
            "host": "localhost",
            "port": 3306,
            "username": "test_user",
            "password": "test_pass",
            "database": "test_db",
            "ssl_enabled": False,
            "connection_timeout": 5
        }
    }

@pytest.fixture
def sample_mongodb_config():
    """Sample MongoDB configuration."""
    return {
        "connection": {
            "host": "localhost",
            "port": 27017,
            "username": "test_user",
            "password": "test_pass",
            "database": "test_db",
            "ssl_enabled": False,
            "connection_timeout": 5
        }
    }

@pytest.fixture
def sample_redis_config():
    """Sample Redis configuration."""
    return {
        "connection": {
            "host": "localhost",
            "port": 6379,
            "password": "test_pass",
            "database": "0",
            "ssl_enabled": False,
            "connection_timeout": 5
        }
    }

@pytest.fixture
def sample_s3_config():
    """Sample S3 configuration."""
    return {
        "connection": {
            "host": "s3.amazonaws.com",
            "port": 443,
            "username": "access_key",
            "password": "secret_key",
            "ssl_enabled": True,
            "connection_timeout": 5,
            "additional_params": {
                "region_name": "us-east-1"
            }
        }
    }

@pytest.fixture
def sample_kafka_config():
    """Sample Kafka configuration."""
    return {
        "connection": {
            "host": "localhost",
            "port": 9092,
            "username": "test_user",
            "password": "test_pass",
            "ssl_enabled": False,
            "connection_timeout": 5
        }
    }

@pytest.fixture
def sample_rest_api_config():
    """Sample REST API configuration."""
    return {
        "connection": {
            "host": "api.example.com",
            "port": 443,
            "username": "api_key",
            "password": "api_secret",
            "ssl_enabled": True,
            "connection_timeout": 5,
            "additional_params": {
                "health_endpoint": "/health"
            }
        }
    }

async def test_validate_postgresql(mocker, sample_postgresql_config):
    """Test PostgreSQL validation."""
    # Mock database connection and query
    mock_conn = mocker.AsyncMock()
    mock_conn.execute.return_value = None
    mock_conn.fetchrow.return_value = {
        "database": "test_db",
        "version": "PostgreSQL 14.0",
        "server_time": datetime.now()
    }
    
    mocker.patch("app.api.core.database.db_pool.get_postgres_conn",
                 return_value=mocker.AsyncMock(__aenter__=mocker.AsyncMock(return_value=mock_conn)))
    
    result = await data_source_validator.validate(
        DataSourceType.POSTGRESQL.value,
        sample_postgresql_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "database" in result.validation_details
    assert "version" in result.validation_details

async def test_validate_mysql(mocker, sample_mysql_config):
    """Test MySQL validation."""
    # Mock aiomysql pool and connection
    mock_cur = mocker.AsyncMock()
    mock_cur.execute.return_value = None
    mock_cur.fetchone.return_value = ("MySQL 8.0", "test_db", datetime.now())
    
    mock_conn = mocker.AsyncMock()
    mock_conn.cursor.return_value = mocker.AsyncMock(__aenter__=mocker.AsyncMock(return_value=mock_cur))
    
    mock_pool = mocker.AsyncMock()
    mock_pool.acquire.return_value = mocker.AsyncMock(__aenter__=mocker.AsyncMock(return_value=mock_conn))
    
    mocker.patch("aiomysql.create_pool", return_value=mock_pool)
    
    result = await data_source_validator.validate(
        DataSourceType.MYSQL.value,
        sample_mysql_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "database" in result.validation_details
    assert "version" in result.validation_details

async def test_validate_mongodb(mocker, sample_mongodb_config):
    """Test MongoDB validation."""
    # Mock MongoDB client
    mock_client = mocker.AsyncMock()
    mock_client.admin.command.return_value = {
        "version": "5.0",
        "uptime": 1000,
        "connections": {"current": 5}
    }
    
    mocker.patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=mock_client)
    
    result = await data_source_validator.validate(
        DataSourceType.MONGODB.value,
        sample_mongodb_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "version" in result.validation_details
    assert "uptime" in result.validation_details

async def test_validate_redis(mocker, sample_redis_config):
    """Test Redis validation."""
    # Mock Redis client
    mock_redis = mocker.AsyncMock()
    mock_redis.info.return_value = {
        "redis_version": "6.2",
        "connected_clients": 10,
        "used_memory_human": "1M"
    }
    
    mocker.patch("aioredis.from_url", return_value=mock_redis)
    
    result = await data_source_validator.validate(
        DataSourceType.REDIS.value,
        sample_redis_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "version" in result.validation_details
    assert "connected_clients" in result.validation_details

async def test_validate_s3(mocker, sample_s3_config):
    """Test S3 validation."""
    # Mock S3 client
    mock_s3 = mocker.AsyncMock()
    mock_s3.list_buckets.return_value = {
        "Buckets": [{"Name": "test-bucket"}],
        "Owner": {"DisplayName": "test-owner"}
    }
    
    mock_session = mocker.AsyncMock()
    mock_session.client.return_value = mocker.AsyncMock(__aenter__=mocker.AsyncMock(return_value=mock_s3))
    
    mocker.patch("aioboto3.Session", return_value=mock_session)
    
    result = await data_source_validator.validate(
        DataSourceType.S3.value,
        sample_s3_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "buckets" in result.validation_details
    assert "owner" in result.validation_details

async def test_validate_kafka(mocker, sample_kafka_config):
    """Test Kafka validation."""
    # Mock Kafka consumer
    mock_consumer = mocker.AsyncMock()
    mock_consumer.topics.return_value = ["topic1", "topic2"]
    mock_consumer.describe_cluster.return_value = mocker.Mock(
        brokers=[1, 2, 3],
        controller_id=1
    )
    
    mocker.patch("aiokafka.AIOKafkaConsumer", return_value=mock_consumer)
    
    result = await data_source_validator.validate(
        DataSourceType.KAFKA.value,
        sample_kafka_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "topics" in result.validation_details
    assert "brokers" in result.validation_details

async def test_validate_rest_api(mocker, sample_rest_api_config):
    """Test REST API validation."""
    # Mock aiohttp client session
    mock_response = mocker.AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"status": "healthy"}
    
    mock_session = mocker.AsyncMock()
    mock_session.get.return_value = mocker.AsyncMock(__aenter__=mocker.AsyncMock(return_value=mock_response))
    
    mocker.patch("aiohttp.ClientSession", return_value=mock_session)
    
    result = await data_source_validator.validate(
        DataSourceType.REST_API.value,
        sample_rest_api_config
    )
    
    assert result.is_valid
    assert result.status == DataSourceStatus.ACTIVE
    assert result.health == DataSourceHealth.HEALTHY
    assert "status_code" in result.validation_details
    assert "headers" in result.validation_details

async def test_validate_unsupported_type():
    """Test validation of unsupported data source type."""
    result = await data_source_validator.validate(
        "unsupported_type",
        {"connection": {}}
    )
    
    assert not result.is_valid
    assert result.status == DataSourceStatus.ERROR
    assert result.health == DataSourceHealth.UNKNOWN
    assert "Unsupported data source type" in result.error_message

async def test_validate_connection_timeout(mocker, sample_postgresql_config):
    """Test validation timeout."""
    # Mock database connection that takes too long
    mock_conn = mocker.AsyncMock()
    mock_conn.execute.side_effect = asyncio.sleep(10)
    
    mocker.patch("app.api.core.database.db_pool.get_postgres_conn",
                 return_value=mocker.AsyncMock(__aenter__=mocker.AsyncMock(return_value=mock_conn)))
    
    result = await data_source_validator.validate(
        DataSourceType.POSTGRESQL.value,
        sample_postgresql_config
    )
    
    assert not result.is_valid
    assert result.status == DataSourceStatus.ERROR
    assert result.health == DataSourceHealth.UNHEALTHY
    assert "Connection timeout" in result.error_message 