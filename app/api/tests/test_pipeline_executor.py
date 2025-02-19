"""
Tests for the pipeline executor service.
"""
import pytest
import asyncio
from datetime import datetime, timezone
from fastapi import HTTPException
from ..models.pipeline import (
    PipelineStatus, PipelineHealth, PipelineMetrics,
    LogLevel
)
from ..services.pipeline_executor import pipeline_executor

@pytest.fixture
def mock_db_pool(mocker):
    """Mock database pool."""
    return mocker.patch('app.api.core.database.db_pool')

@pytest.fixture
def mock_conn(mocker):
    """Mock database connection."""
    return mocker.AsyncMock()

@pytest.fixture
def sample_pipeline():
    """Sample pipeline configuration."""
    return {
        "id": 1,
        "name": "Test Pipeline",
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
        "schedule": "0 * * * *"
    }

@pytest.fixture
def sample_metrics():
    """Sample pipeline metrics."""
    return {
        "throughput": 100.0,
        "latency": 50.0,
        "error_rate": 0.1,
        "success_rate": 99.9,
        "processed_records": 1000,
        "failed_records": 1
    }

async def test_start_pipeline(mock_db_pool, mock_conn, sample_pipeline):
    """Test starting a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = sample_pipeline

    # Execute
    await pipeline_executor.start_pipeline(1)

    # Assert
    assert 1 in pipeline_executor._running_pipelines
    assert isinstance(pipeline_executor._pipeline_metrics[1], PipelineMetrics)
    mock_conn.fetchrow.assert_called_once_with("""
        SELECT id, name, type, config, schedule
        FROM pipelines
        WHERE id = $1
    """, 1)
    mock_conn.execute.assert_called_with("""
        INSERT INTO pipeline_logs (
            pipeline_id, level, message, details
        ) VALUES ($1, $2, $3, $4)
    """, 1, LogLevel.INFO, "Pipeline Test Pipeline started", {"type": "etl"})

async def test_start_pipeline_already_running(mock_db_pool, mock_conn):
    """Test starting an already running pipeline."""
    # Setup
    pipeline_executor._running_pipelines[1] = asyncio.create_task(asyncio.sleep(0))

    # Execute and Assert
    with pytest.raises(HTTPException) as exc_info:
        await pipeline_executor.start_pipeline(1)
    assert exc_info.value.status_code == 400
    assert "Pipeline is already running" in exc_info.value.detail

    # Cleanup
    pipeline_executor._running_pipelines[1].cancel()
    del pipeline_executor._running_pipelines[1]

async def test_stop_pipeline(mock_db_pool, mock_conn):
    """Test stopping a pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    pipeline_executor._running_pipelines[1] = asyncio.create_task(asyncio.sleep(0))
    pipeline_executor._pipeline_metrics[1] = PipelineMetrics(
        throughput=0.0,
        latency=0.0,
        error_rate=0.0,
        success_rate=0.0,
        processed_records=0,
        failed_records=0
    )

    # Execute
    await pipeline_executor.stop_pipeline(1)

    # Assert
    assert 1 not in pipeline_executor._running_pipelines
    assert 1 not in pipeline_executor._pipeline_metrics
    mock_conn.execute.assert_has_calls([
        mocker.call("""
            UPDATE pipelines
            SET status = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, 1, PipelineStatus.STOPPED),
        mocker.call("""
            INSERT INTO pipeline_logs (
                pipeline_id, level, message, details
            ) VALUES ($1, $2, $3, $4)
        """, 1, LogLevel.INFO, "Pipeline stopped", {"final_metrics": {
            "throughput": 0.0,
            "latency": 0.0,
            "error_rate": 0.0,
            "success_rate": 0.0,
            "processed_records": 0,
            "failed_records": 0
        }})
    ])

async def test_stop_pipeline_not_running(mock_db_pool, mock_conn):
    """Test stopping a non-running pipeline."""
    # Execute and Assert
    with pytest.raises(HTTPException) as exc_info:
        await pipeline_executor.stop_pipeline(1)
    assert exc_info.value.status_code == 400
    assert "Pipeline is not running" in exc_info.value.detail

async def test_get_pipeline_status(mock_db_pool, mock_conn, sample_metrics):
    """Test getting pipeline status."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = {
        "status": PipelineStatus.RUNNING,
        "health": PipelineHealth.HEALTHY,
        "last_run": datetime.now(timezone.utc)
    }
    pipeline_executor._running_pipelines[1] = asyncio.create_task(asyncio.sleep(0))
    pipeline_executor._pipeline_metrics[1] = PipelineMetrics(**sample_metrics)

    # Execute
    status = await pipeline_executor.get_pipeline_status(1)

    # Assert
    assert status["status"] == PipelineStatus.RUNNING
    assert status["health"] == PipelineHealth.HEALTHY
    assert status["is_running"] is True
    assert isinstance(status["metrics"], PipelineMetrics)
    assert isinstance(status["last_run"], datetime)
    mock_conn.fetchrow.assert_called_once_with("""
        SELECT status, health, last_run
        FROM pipelines
        WHERE id = $1
    """, 1)

    # Cleanup
    pipeline_executor._running_pipelines[1].cancel()
    del pipeline_executor._running_pipelines[1]
    del pipeline_executor._pipeline_metrics[1]

async def test_get_pipeline_status_not_found(mock_db_pool, mock_conn):
    """Test getting status of non-existent pipeline."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    mock_conn.fetchrow.return_value = None

    # Execute and Assert
    with pytest.raises(HTTPException) as exc_info:
        await pipeline_executor.get_pipeline_status(1)
    assert exc_info.value.status_code == 404
    assert "Pipeline not found" in exc_info.value.detail

async def test_update_metrics():
    """Test updating pipeline metrics."""
    # Setup
    pipeline_executor._pipeline_metrics[1] = PipelineMetrics(
        throughput=0.0,
        latency=0.0,
        error_rate=0.0,
        success_rate=0.0,
        processed_records=0,
        failed_records=0
    )

    # Execute
    await pipeline_executor._update_metrics(1, 100, 1)

    # Assert
    metrics = pipeline_executor._pipeline_metrics[1]
    assert metrics.processed_records == 100
    assert metrics.failed_records == 1
    assert metrics.success_rate == 99.0
    assert metrics.error_rate == 1.0

    # Cleanup
    del pipeline_executor._pipeline_metrics[1]

async def test_log_pipeline_event(mock_db_pool, mock_conn):
    """Test logging pipeline event."""
    # Setup
    mock_db_pool.postgres_connection.return_value.__aenter__.return_value = mock_conn
    details = {"test": "data"}

    # Execute
    await pipeline_executor._log_pipeline_event(
        1, LogLevel.INFO, "Test message", details
    )

    # Assert
    mock_conn.execute.assert_called_once_with("""
        INSERT INTO pipeline_logs (
            pipeline_id, level, message, details
        ) VALUES ($1, $2, $3, $4)
    """, 1, LogLevel.INFO, "Test message", details) 