"""
Tests for the pipeline service.
"""
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from ..models.pipeline import (
    PipelineCreate, PipelineUpdate, PipelineConfig,
    PipelineType, PipelineStatus, PipelineHealth
)
from ..services.pipeline_service import pipeline_service

@pytest.fixture
def mock_db_pool(mocker):
    """Mock database pool."""
    return mocker.patch('app.api.core.database.db_pool')

@pytest.fixture
def mock_conn(mocker):
    """Mock database connection."""
    return mocker.AsyncMock()

@pytest.fixture
def sample_pipeline_config():
    """Sample pipeline configuration."""
    return PipelineConfig(
        source_config={
            "type": "postgres",
            "connection_details": {
                "host": "localhost",
                "port": 5432,
                "database": "test_db"
            }
        },
        destination_config={
            "type": "clickhouse",
            "connection_details": {
                "host": "localhost",
                "port": 8123,
                "database": "test_db"
            }
        }
    )

@pytest.fixture
def sample_pipeline_create(sample_pipeline_config):
    """Sample pipeline creation data."""
    return PipelineCreate(
        name="Test Pipeline",
        description="Test pipeline description",
        type=PipelineType.ETL,
        config=sample_pipeline_config,
        schedule="0 * * * *",
        data_source_id=1
    )

@pytest.fixture
def sample_pipeline_db():
    """Sample pipeline database record."""
    return {
        "id": 1,
        "name": "Test Pipeline",
        "description": "Test pipeline description",
        "type": "etl",
        "config": {
            "source_config": {
                "type": "postgres",
                "connection_details": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_db"
                }
            },
            "destination_config": {
                "type": "clickhouse",
                "connection_details": {
                    "host": "localhost",
                    "port": 8123,
                    "database": "test_db"
                }
            }
        },
        "schedule": "0 * * * *",
        "status": "created",
        "health": "unknown",
        "version": "1.0",
        "organization_id": 1,
        "data_source_id": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_run": None
    }

async def test_list_pipelines(mock_db_pool, mock_conn, sample_pipeline_db):
    """Test listing pipelines."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetch.side_effect = [
        [{"organization_id": 1}],  # org_ids
        [sample_pipeline_db]  # pipelines
    ]

    # Execute
    result = await pipeline_service.list_pipelines(user_id=1)

    # Assert
    assert len(result) == 1
    assert result[0]["id"] == sample_pipeline_db["id"]
    assert result[0]["name"] == sample_pipeline_db["name"]
    mock_conn.fetch.assert_has_calls([
        mocker.call("""
            SELECT organization_id
            FROM organization_members
            WHERE user_id = $1
        """, 1),
        mocker.call("""
            SELECT p.id, p.name, p.description, p.config, p.type,
                   p.schedule, p.status, p.health, p.version,
                   p.organization_id, p.data_source_id,
                   p.created_at, p.updated_at, p.last_run
            FROM pipelines p
            JOIN data_sources ds ON p.data_source_id = ds.id
            WHERE ds.organization_id = ANY($1::bigint[])
            ORDER BY p.created_at DESC
        """, [1])
    ])

async def test_create_pipeline(mock_db_pool, mock_conn, sample_pipeline_create, sample_pipeline_db):
    """Test creating a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_conn.fetchrow.side_effect = [
        {"id": 1, "organization_id": 1},  # access check
        sample_pipeline_db  # new pipeline
    ]

    # Execute
    result = await pipeline_service.create_pipeline(sample_pipeline_create, user_id=1)

    # Assert
    assert result["id"] == sample_pipeline_db["id"]
    assert result["name"] == sample_pipeline_db["name"]
    mock_conn.fetchrow.assert_has_calls([
        mocker.call("""
            SELECT ds.id, ds.organization_id
            FROM data_sources ds
            JOIN organization_members om ON ds.organization_id = om.organization_id
            WHERE ds.id = $1 AND om.user_id = $2
        """, 1, 1),
        mocker.call("""
            INSERT INTO pipelines (
                name, description, config, type, schedule,
                status, health, version, data_source_id,
                organization_id
            )
            VALUES ($1, $2, $3, $4, $5, 'created', 'unknown', '1.0', $6, $7)
            RETURNING id, name, description, config, type,
                      schedule, status, health, version,
                      organization_id, data_source_id,
                      created_at, updated_at, last_run
        """, "Test Pipeline", "Test pipeline description",
        sample_pipeline_create.config.dict(), "etl", "0 * * * *", 1, 1)
    ])

async def test_get_pipeline(mock_db_pool, mock_conn, sample_pipeline_db):
    """Test getting a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = sample_pipeline_db

    # Execute
    result = await pipeline_service.get_pipeline(pipeline_id=1, user_id=1)

    # Assert
    assert result["id"] == sample_pipeline_db["id"]
    assert result["name"] == sample_pipeline_db["name"]
    mock_conn.fetchrow.assert_called_once_with("""
        SELECT p.id, p.name, p.description, p.config, p.type,
               p.schedule, p.status, p.health, p.version,
               p.organization_id, p.data_source_id,
               p.created_at, p.updated_at, p.last_run
        FROM pipelines p
        JOIN data_sources ds ON p.data_source_id = ds.id
        JOIN organization_members om ON ds.organization_id = om.organization_id
        WHERE p.id = $1 AND om.user_id = $2
    """, 1, 1)

async def test_update_pipeline(mock_db_pool, mock_conn, sample_pipeline_db):
    """Test updating a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_conn.fetchrow.side_effect = [
        {"id": 1, "status": "created"},  # existing pipeline
        {**sample_pipeline_db, "name": "Updated Pipeline"}  # updated pipeline
    ]
    
    update_data = PipelineUpdate(name="Updated Pipeline")

    # Execute
    result = await pipeline_service.update_pipeline(1, update_data, user_id=1)

    # Assert
    assert result["name"] == "Updated Pipeline"
    mock_conn.fetchrow.assert_has_calls([
        mocker.call("""
            SELECT p.id, p.status
            FROM pipelines p
            JOIN data_sources ds ON p.data_source_id = ds.id
            JOIN organization_members om ON ds.organization_id = om.organization_id
            WHERE p.id = $1 AND om.user_id = $2
        """, 1, 1),
        mocker.call("""
            UPDATE pipelines 
            SET name = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id, name, description, config, type,
                      schedule, status, health, version,
                      organization_id, data_source_id,
                      created_at, updated_at, last_run
        """, 1, "Updated Pipeline")
    ])

async def test_delete_pipeline(mock_db_pool, mock_conn):
    """Test deleting a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_conn.fetchrow.return_value = {"id": 1}

    # Execute
    await pipeline_service.delete_pipeline(1, user_id=1)

    # Assert
    mock_conn.fetchrow.assert_called_once_with("""
        SELECT p.id
        FROM pipelines p
        JOIN data_sources ds ON p.data_source_id = ds.id
        JOIN organization_members om ON ds.organization_id = om.organization_id
        WHERE p.id = $1 AND om.user_id = $2
    """, 1, 1)
    mock_conn.execute.assert_has_calls([
        mocker.call("""
            DELETE FROM pipeline_metrics WHERE pipeline_id = $1
        """, 1),
        mocker.call("""
            DELETE FROM pipeline_logs WHERE pipeline_id = $1
        """, 1),
        mocker.call("""
            DELETE FROM pipelines WHERE id = $1
        """, 1)
    ])

async def test_start_pipeline(mock_db_pool, mock_conn):
    """Test starting a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.side_effect = [
        {"id": 1, "status": "created", "config": {}, "health": "unknown"},  # pipeline
        {"status": "running", "health": "unknown", "last_run": datetime.now(timezone.utc)},  # updated
        {"throughput": 0, "latency": 0, "error_rate": 0, "success_rate": 0,
         "processed_records": 0, "failed_records": 0}  # metrics
    ]

    # Execute
    result = await pipeline_service.start_pipeline(1, user_id=1)

    # Assert
    assert result.status == PipelineStatus.RUNNING
    mock_conn.fetchrow.assert_has_calls([
        mocker.call("""
            SELECT p.id, p.status, p.config, p.health
            FROM pipelines p
            JOIN data_sources ds ON p.data_source_id = ds.id
            JOIN organization_members om ON ds.organization_id = om.organization_id
            WHERE p.id = $1 AND om.user_id = $2
        """, 1, 1),
        mocker.call("""
            UPDATE pipelines
            SET status = $2,
                last_run = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING status, health, last_run
        """, 1, PipelineStatus.RUNNING)
    ])

async def test_stop_pipeline(mock_db_pool, mock_conn):
    """Test stopping a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.side_effect = [
        {"id": 1, "status": "running", "config": {}, "health": "healthy"},  # pipeline
        {"status": "stopped", "health": "healthy", "last_run": datetime.now(timezone.utc)},  # updated
        {"throughput": 100, "latency": 50, "error_rate": 0.1, "success_rate": 99.9,
         "processed_records": 1000, "failed_records": 1}  # metrics
    ]

    # Execute
    result = await pipeline_service.stop_pipeline(1, user_id=1)

    # Assert
    assert result.status == PipelineStatus.STOPPED
    mock_conn.fetchrow.assert_has_calls([
        mocker.call("""
            SELECT p.id, p.status, p.config, p.health
            FROM pipelines p
            JOIN data_sources ds ON p.data_source_id = ds.id
            JOIN organization_members om ON ds.organization_id = om.organization_id
            WHERE p.id = $1 AND om.user_id = $2
        """, 1, 1),
        mocker.call("""
            UPDATE pipelines
            SET status = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING status, health, last_run
        """, 1, PipelineStatus.STOPPED)
    ])

async def test_get_pipeline_logs(mock_db_pool, mock_conn):
    """Test getting pipeline logs."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    now = datetime.now(timezone.utc)
    mock_conn.fetchrow.return_value = {"id": 1}
    mock_conn.fetch.return_value = [
        {"timestamp": now, "level": "info", "message": "Pipeline started", "details": None},
        {"timestamp": now, "level": "info", "message": "Processing data", "details": {"count": 100}}
    ]
    mock_conn.fetchval.return_value = 2

    # Execute
    result = await pipeline_service.get_pipeline_logs(1, user_id=1)

    # Assert
    assert len(result.logs) == 2
    assert result.total_entries == 2
    mock_conn.fetchrow.assert_called_once_with("""
        SELECT p.id
        FROM pipelines p
        JOIN data_sources ds ON p.data_source_id = ds.id
        JOIN organization_members om ON ds.organization_id = om.organization_id
        WHERE p.id = $1 AND om.user_id = $2
    """, 1, 1)

async def test_validate_status_transition():
    """Test pipeline status transition validation."""
    # Valid transitions
    pipeline_service._validate_status_transition(PipelineStatus.CREATED, PipelineStatus.RUNNING)
    pipeline_service._validate_status_transition(PipelineStatus.RUNNING, PipelineStatus.STOPPED)
    pipeline_service._validate_status_transition(PipelineStatus.STOPPED, PipelineStatus.RUNNING)

    # Invalid transitions
    with pytest.raises(HTTPException) as exc_info:
        pipeline_service._validate_status_transition(PipelineStatus.CREATED, PipelineStatus.COMPLETED)
    assert exc_info.value.status_code == 400
    assert "Invalid status transition" in exc_info.value.detail 