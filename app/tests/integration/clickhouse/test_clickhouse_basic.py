import pytest
import logging
from clickhouse_driver import Client

logger = logging.getLogger(__name__)

@pytest.mark.integration
def test_clickhouse_connection(clickhouse_client: Client):
    """Test basic ClickHouse operations."""
    # Create a test table
    logger.info("Creating test table...")
    clickhouse_client.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id UInt32,
            name String
        ) ENGINE = Memory
    """)
    
    try:
        # Insert test data
        logger.info("Inserting test data...")
        test_data = [(1, "test1"), (2, "test2")]
        clickhouse_client.execute(
            "INSERT INTO test_table (id, name) VALUES",
            test_data
        )
        
        # Query the data
        logger.info("Querying test data...")
        result = clickhouse_client.execute("SELECT * FROM test_table ORDER BY id")
        
        # Verify results
        assert len(result) == 2, f"Expected 2 rows, got {len(result)}"
        assert result == test_data, f"Expected {test_data}, got {result}"
        logger.info("Test passed!")
        
    finally:
        # Cleanup
        logger.info("Cleaning up test table...")
        clickhouse_client.execute("DROP TABLE IF EXISTS test_table") 