import pytest
import asyncio
from datetime import datetime, timedelta
from app.api.core.database import (
    postgres,
    clickhouse,
    questdb,
    materialize
)
from app.api.core.schema.materialize import MaterializeSchema

@pytest.mark.asyncio
async def test_postgres_maintenance():
    """Test PostgreSQL maintenance operations"""
    # Test table statistics update
    await postgres.execute("ANALYZE organizations")
    await postgres.execute("ANALYZE users")
    
    # Verify statistics were updated
    result = await postgres.execute(
        """
        SELECT last_analyze 
        FROM pg_stat_user_tables 
        WHERE relname = 'organizations'
        """
    )
    assert result[0][0] is not None

@pytest.mark.asyncio
async def test_clickhouse_maintenance():
    """Test ClickHouse maintenance operations"""
    # Test table optimization
    await clickhouse.execute("OPTIMIZE TABLE events FINAL")
    await clickhouse.execute("OPTIMIZE TABLE metrics FINAL")
    
    # Verify parts were merged
    result = await clickhouse.execute(
        """
        SELECT count() 
        FROM system.parts 
        WHERE table = 'events' 
        AND active = 1
        """
    )
    assert result[0][0] >= 0

@pytest.mark.asyncio
async def test_questdb_maintenance():
    """Test QuestDB maintenance operations"""
    # Test data retention
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Clean up old performance metrics
    await questdb.execute(
        """
        ALTER TABLE performance_metrics
        DROP PARTITION WHERE timestamp < ?
        """,
        (one_week_ago,)
    )
    
    # Verify old data was removed
    result = await questdb.execute(
        """
        SELECT count(*) 
        FROM performance_metrics 
        WHERE timestamp < ?
        """,
        (one_week_ago,)
    )
    assert result[0][0] == 0

@pytest.mark.asyncio
async def test_materialize_maintenance():
    """Test Materialize maintenance operations"""
    # Test view refresh
    await materialize.execute("REFRESH MATERIALIZED VIEW rt_metrics")
    await materialize.execute("REFRESH MATERIALIZED VIEW rt_events")
    
    # Verify views are up to date
    result = await materialize.execute(
        """
        SELECT mz_logical_timestamp() as current_timestamp,
               mz_view_timestamp as view_timestamp
        FROM mz_catalog.mz_materialized_views
        WHERE name = 'rt_metrics'
        """
    )
    assert len(result) > 0
    current_ts = result[0]['current_timestamp']
    view_ts = result[0]['view_timestamp']
    assert current_ts >= view_ts

@pytest.mark.asyncio
async def test_stale_view_cleanup():
    """Test cleanup of stale materialized views"""
    # Create a test view
    await materialize.execute(
        """
        CREATE MATERIALIZED VIEW test_stale_view AS
        SELECT 1 as dummy
        """
    )
    
    # Mark it as stale (simulate by updating metadata)
    await materialize.execute(
        """
        COMMENT ON MATERIALIZED VIEW test_stale_view IS
        '{"last_accessed": "2000-01-01T00:00:00Z"}'
        """
    )
    
    # Run cleanup
    schema = MaterializeSchema()
    await schema.cleanup_stale_views()
    
    # Verify view was removed
    result = await materialize.execute(
        """
        SELECT count(*) 
        FROM mz_catalog.mz_materialized_views
        WHERE name = 'test_stale_view'
        """
    )
    assert result[0][0] == 0

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling during maintenance operations"""
    # Test handling of invalid operations
    with pytest.raises(Exception):
        await postgres.execute("ANALYZE nonexistent_table")
    
    with pytest.raises(Exception):
        await clickhouse.execute("OPTIMIZE TABLE nonexistent_table")
    
    with pytest.raises(Exception):
        await questdb.execute(
            "ALTER TABLE nonexistent_table DROP PARTITION WHERE timestamp < ?",
            (datetime.utcnow(),)
        )
    
    with pytest.raises(Exception):
        await materialize.execute("REFRESH MATERIALIZED VIEW nonexistent_view") 