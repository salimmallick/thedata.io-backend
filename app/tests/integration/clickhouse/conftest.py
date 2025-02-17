import pytest
import logging
import os
from clickhouse_driver import Client
from typing import Generator

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def clickhouse_client() -> Generator[Client, None, None]:
    """Fixture to provide a ClickHouse client for tests."""
    client = Client(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse-test"),
        port=int(os.environ.get("CLICKHOUSE_PORT", "9000")),
        database=os.environ.get("CLICKHOUSE_DB", "default"),
        user=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
        connect_timeout=10
    )
    
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
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All connection attempts failed: {e}")
                    raise
        
        yield client
    except Exception as e:
        logger.error(f"Failed to connect to ClickHouse: {e}")
        raise
    finally:
        logger.info("Cleaning up ClickHouse connection...")
        # No explicit cleanup needed for ClickHouse client
        logger.info("ClickHouse cleanup complete") 