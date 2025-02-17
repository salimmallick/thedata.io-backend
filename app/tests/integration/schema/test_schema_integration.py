import pytest
import asyncio
from app.api.core.schema.init import SchemaInitializer
from app.api.core.database import (
    postgres,
    clickhouse,
    questdb,
    materialize
)

@pytest.fixture(scope="module")
async def schema_initializer():
    """Fixture to provide schema initializer instance"""
    initializer = SchemaInitializer()
    await initializer.initialize_all()
    yield initializer

@pytest.mark.asyncio
async def test_schema_initialization(schema_initializer):
    """Test that all schemas can be initialized successfully"""
    result = await schema_initializer.initialize_all()
    assert result is True

@pytest.mark.asyncio
async def test_schema_verification(schema_initializer):
    """Test that all schemas can be verified successfully"""
    result = await schema_initializer.verify_all()
    assert result is True

@pytest.mark.asyncio
async def test_database_health_check(schema_initializer):
    """Test health check functionality for all databases"""
    health_status = await schema_initializer.health_check()
    assert all(health_status.values()), f"Not all databases are healthy: {health_status}"

@pytest.mark.asyncio
async def test_postgres_schema():
    """Test PostgreSQL schema specific functionality"""
    # Test organization table
    result = await postgres.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'organizations')"
    )
    assert result[0][0] is True

    # Test users table
    result = await postgres.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
    )
    assert result[0][0] is True

@pytest.mark.asyncio
async def test_clickhouse_schema():
    """Test ClickHouse schema specific functionality"""
    # Test events table
    result = await clickhouse.execute("SHOW TABLES LIKE 'events'")
    assert len(result) > 0

    # Test metrics table
    result = await clickhouse.execute("SHOW TABLES LIKE 'metrics'")
    assert len(result) > 0

@pytest.mark.asyncio
async def test_questdb_schema():
    """Test QuestDB schema specific functionality"""
    # Test performance metrics table
    result = await questdb.execute("SHOW TABLES LIKE 'performance_metrics'")
    assert len(result) > 0

    # Test system metrics table
    result = await questdb.execute("SHOW TABLES LIKE 'system_metrics'")
    assert len(result) > 0

@pytest.mark.asyncio
async def test_materialize_views():
    """Test Materialize views and sinks"""
    # Test real-time metrics view
    result = await materialize.execute("SHOW MATERIALIZED VIEWS LIKE 'rt_metrics'")
    assert len(result) > 0

    # Test alert sinks
    result = await materialize.execute("SHOW SINKS LIKE 'error_rate_alerts'")
    assert len(result) > 0 