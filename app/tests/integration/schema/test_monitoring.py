import pytest
import asyncio
from datetime import datetime, timedelta
from app.api.core.database import (
    postgres,
    clickhouse,
    questdb,
    materialize
)
from app.api.core.metrics import metrics

@pytest.mark.asyncio
async def test_postgres_metrics():
    """Test PostgreSQL monitoring metrics"""
    # Test connection pool metrics
    assert metrics.db_connection_pool_size.labels(
        database="postgres"
    )._value is not None
    
    # Test query latency metrics
    start_time = datetime.utcnow()
    await postgres.execute("SELECT 1")
    end_time = datetime.utcnow()
    
    # Verify query duration was recorded
    query_duration = (end_time - start_time).total_seconds()
    assert metrics.db_query_duration_seconds.labels(
        database="postgres",
        query_type="select"
    )._value >= query_duration

@pytest.mark.asyncio
async def test_clickhouse_metrics():
    """Test ClickHouse monitoring metrics"""
    # Test connection metrics
    assert metrics.db_connection_pool_size.labels(
        database="clickhouse"
    )._value is not None
    
    # Test query latency metrics
    start_time = datetime.utcnow()
    await clickhouse.execute("SELECT 1")
    end_time = datetime.utcnow()
    
    query_duration = (end_time - start_time).total_seconds()
    assert metrics.db_query_duration_seconds.labels(
        database="clickhouse",
        query_type="select"
    )._value >= query_duration
    
    # Test table size metrics
    result = await clickhouse.execute(
        "SELECT count() FROM system.tables WHERE database = currentDatabase()"
    )
    table_count = result[0][0]
    assert metrics.db_table_count.labels(
        database="clickhouse"
    )._value == table_count

@pytest.mark.asyncio
async def test_questdb_metrics():
    """Test QuestDB monitoring metrics"""
    # Test connection metrics
    assert metrics.db_connection_pool_size.labels(
        database="questdb"
    )._value is not None
    
    # Test query latency metrics
    start_time = datetime.utcnow()
    await questdb.execute("SELECT 1")
    end_time = datetime.utcnow()
    
    query_duration = (end_time - start_time).total_seconds()
    assert metrics.db_query_duration_seconds.labels(
        database="questdb",
        query_type="select"
    )._value >= query_duration

@pytest.mark.asyncio
async def test_materialize_metrics():
    """Test Materialize monitoring metrics"""
    # Test connection metrics
    assert metrics.db_connection_pool_size.labels(
        database="materialize"
    )._value is not None
    
    # Test view metrics
    result = await materialize.execute(
        "SELECT count(*) FROM mz_catalog.mz_materialized_views"
    )
    view_count = result[0][0]
    assert metrics.materialize_view_count._value == view_count
    
    # Test sink metrics
    result = await materialize.execute(
        "SELECT count(*) FROM mz_catalog.mz_sinks"
    )
    sink_count = result[0][0]
    assert metrics.materialize_sink_count._value == sink_count

@pytest.mark.asyncio
async def test_error_metrics():
    """Test error tracking metrics"""
    # Test database error counter
    try:
        await postgres.execute("SELECT * FROM nonexistent_table")
    except Exception:
        pass
    
    assert metrics.db_error_count.labels(
        database="postgres",
        error_type="query_error"
    )._value > 0
    
    # Test connection error counter
    try:
        await clickhouse.execute("SELECT * FROM nonexistent_table")
    except Exception:
        pass
    
    assert metrics.db_error_count.labels(
        database="clickhouse",
        error_type="query_error"
    )._value > 0

@pytest.mark.asyncio
async def test_performance_metrics():
    """Test database performance metrics"""
    # Test query performance metrics
    queries = [
        (postgres, "SELECT 1"),
        (clickhouse, "SELECT 1"),
        (questdb, "SELECT 1"),
        (materialize, "SELECT 1")
    ]
    
    for db, query in queries:
        # Measure query latency
        start_time = datetime.utcnow()
        await db.execute(query)
        end_time = datetime.utcnow()
        
        query_duration = (end_time - start_time).total_seconds()
        assert metrics.db_query_duration_seconds.labels(
            database=db.__class__.__name__.lower(),
            query_type="select"
        )._value >= query_duration 