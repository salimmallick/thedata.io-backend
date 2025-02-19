"""
Tests for the data source service.
"""
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from ..models.data_source import (
    DataSourceCreate, DataSourceUpdate, DataSourceConfig,
    DataSourceType, DataSourceStatus, DataSourceHealth,
    ConnectionConfig
)
from ..services.data_source_service import data_source_service

@pytest.fixture
def mock_db_pool(mocker):
    """Mock database pool."""
    return mocker.patch('app.api.core.database.db_pool')

@pytest.fixture
def mock_conn(mocker):
    """Mock database connection."""
    return mocker.AsyncMock()

@pytest.fixture
def sample_connection_config():
    """Sample connection configuration."""
    return ConnectionConfig(
        host="localhost",
        port=5432,
        username="test_user",
        password="test_pass",
        database="test_db",
        ssl_enabled=False,
        connection_timeout=30
    )

@pytest.fixture
def sample_data_source_config(sample_connection_config):
    """Sample data source configuration."""
    return DataSourceConfig(
        connection=sample_connection_config,
        schema_config={
            "tables": ["users", "orders"],
            "exclude_tables": ["audit_logs"]
        },
        sync_config={
            "frequency": "daily",
            "max_rows": 10000
        }
    )

@pytest.fixture
def sample_data_source_create(sample_data_source_config):
    """Sample data source creation data."""
    return DataSourceCreate(
        name="Test PostgreSQL Source",
        description="Test data source for PostgreSQL",
        type=DataSourceType.POSTGRESQL,
        config=sample_data_source_config,
        organization_id=1,
        tags=["test", "postgresql"]
    )

@pytest.fixture
def sample_data_source_db():
    """Sample data source database record."""
    return {
        "id": 1,
        "name": "Test PostgreSQL Source",
        "description": "Test data source for PostgreSQL",
        "type": DataSourceType.POSTGRESQL.value,
        "config": {
            "connection": {
                "host": "localhost",
                "port": 5432,
                "username": "test_user",
                "password": "test_pass",
                "database": "test_db",
                "ssl_enabled": False,
                "connection_timeout": 30
            },
            "schema_config": {
                "tables": ["users", "orders"],
                "exclude_tables": ["audit_logs"]
            },
            "sync_config": {
                "frequency": "daily",
                "max_rows": 10000
            }
        },
        "tags": ["test", "postgresql"],
        "status": DataSourceStatus.INACTIVE.value,
        "health": DataSourceHealth.UNKNOWN.value,
        "organization_id": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_validated": None
    }

async def test_list_data_sources(mock_db_pool, mock_conn, sample_data_source_db):
    """Test listing data sources."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetch.return_value = [sample_data_source_db]
    
    # Execute
    result = await data_source_service.list_data_sources(user_id=1)
    
    # Assert
    assert len(result) == 1
    assert result[0]["id"] == sample_data_source_db["id"]
    assert result[0]["name"] == sample_data_source_db["name"]
    mock_conn.fetch.assert_called_once()

async def test_create_data_source(mock_db_pool, mock_conn, sample_data_source_create, sample_data_source_db):
    """Test creating a data source."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.side_effect = [
        {"id": 1},  # org access check
        None,       # name uniqueness check
        sample_data_source_db  # creation result
    ]
    
    # Execute
    result = await data_source_service.create_data_source(sample_data_source_create, user_id=1)
    
    # Assert
    assert result["id"] == sample_data_source_db["id"]
    assert result["name"] == sample_data_source_db["name"]
    assert mock_conn.fetchrow.call_count == 3

async def test_get_data_source(mock_db_pool, mock_conn, sample_data_source_db):
    """Test getting a data source."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = sample_data_source_db
    
    # Execute
    result = await data_source_service.get_data_source(source_id=1, user_id=1)
    
    # Assert
    assert result["id"] == sample_data_source_db["id"]
    assert result["name"] == sample_data_source_db["name"]
    mock_conn.fetchrow.assert_called_once()

async def test_update_data_source(mock_db_pool, mock_conn, sample_data_source_db):
    """Test updating a data source."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.side_effect = [
        sample_data_source_db,  # get current
        None,                   # name uniqueness check
        {**sample_data_source_db, "name": "Updated Name"}  # update result
    ]
    
    update_data = DataSourceUpdate(name="Updated Name")
    
    # Execute
    result = await data_source_service.update_data_source(source_id=1, source_update=update_data, user_id=1)
    
    # Assert
    assert result["name"] == "Updated Name"
    assert mock_conn.fetchrow.call_count == 3

async def test_delete_data_source(mock_db_pool, mock_conn):
    """Test deleting a data source."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = {"id": 1}
    
    # Execute
    await data_source_service.delete_data_source(source_id=1, user_id=1)
    
    # Assert
    assert mock_conn.execute.call_count == 2  # Delete pipelines and data source

async def test_validate_connection(mock_db_pool, mock_conn, sample_data_source_db):
    """Test validating a data source connection."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = sample_data_source_db
    
    # Execute
    result = await data_source_service.validate_connection(source_id=1, user_id=1)
    
    # Assert
    assert isinstance(result.is_valid, bool)
    assert isinstance(result.status, DataSourceStatus)
    assert isinstance(result.health, DataSourceHealth)
    assert mock_conn.execute.call_count == 2  # Update status before and after validation

async def test_get_metrics(mock_db_pool, mock_conn, sample_data_source_db):
    """Test getting data source metrics."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.side_effect = [
        sample_data_source_db,  # get data source
        {  # get metrics
            "latency": 100.0,
            "error_rate": 0.1,
            "success_rate": 99.9,
            "total_records": 1000,
            "sync_duration": 60.0,
            "last_sync": datetime.now(timezone.utc)
        }
    ]
    
    # Execute
    result = await data_source_service.get_metrics(source_id=1, user_id=1)
    
    # Assert
    assert result.latency == 100.0
    assert result.error_rate == 0.1
    assert result.success_rate == 99.9
    assert result.total_records == 1000
    assert mock_conn.fetchrow.call_count == 2 