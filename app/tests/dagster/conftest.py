import pytest
import os
import sys
import time
import httpx
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, project_root)

from dagster import build_op_context, build_resources, DagsterInstance
from app.dagster.repository import defs
from app.api.services.materialize import materialize_service
from app.api.services.clickhouse import clickhouse_service
from app.api.services.questdb import questdb_service

# Override service configurations for testing
os.environ.update({
    'CLICKHOUSE_HOST': os.getenv('CLICKHOUSE_HOST', 'clickhouse-test'),
    'QUESTDB_HOST': os.getenv('QUESTDB_HOST', 'questdb-test'),
    'NATS_URL': os.getenv('NATS_URL', 'nats://nats-test:4222'),
    'MATERIALIZE_HOST': os.getenv('MATERIALIZE_HOST', 'materialize-test')
})

def wait_for_service(url: str, timeout: int = 30):
    """Wait for a service to be ready."""
    start_time = time.time()
    while True:
        try:
            response = httpx.get(url)
            if response.status_code == 200:
                return True
        except Exception:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Service {url} not ready after {timeout} seconds")
            time.sleep(1)

@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Wait for all required services to be ready."""
    services = [
        "http://clickhouse-test:8123/ping",
        "http://questdb-test:9000/health",
        "http://materialize-test:6875/status",
        "http://nats-test:8222/healthz"
    ]
    
    for service_url in services:
        wait_for_service(service_url)

@pytest.fixture(scope="session")
def dagster_instance():
    """Provide a Dagster instance for testing."""
    instance = DagsterInstance.ephemeral()
    return instance

@pytest.fixture(scope="session")
def dagster_resources():
    """Provide test resources for Dagster operations."""
    resources = {
        "materialize": materialize_service,
        "clickhouse": clickhouse_service,
        "questdb": questdb_service,
    }
    with build_resources(resources=resources) as context:
        yield context

@pytest.fixture(scope="function")
def op_context(dagster_instance):
    """Provide a context for testing individual operations."""
    return build_op_context(instance=dagster_instance)

@pytest.fixture(scope="session")
def test_repository():
    """Provide access to the Dagster repository definition."""
    return defs

@pytest.fixture(scope="function")
async def setup_test_tables(dagster_resources):
    """Setup test tables in all databases."""
    # ClickHouse test tables
    await dagster_resources.resources.clickhouse.execute("""
        CREATE TABLE IF NOT EXISTS test_events (
            event_id String,
            timestamp DateTime64(9),
            event_type String,
            event_name String,
            properties String,
            context String
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, event_type)
    """)
    
    # QuestDB test tables
    await dagster_resources.resources.questdb.execute("""
        CREATE TABLE IF NOT EXISTS test_metrics (
            ts TIMESTAMP,
            metric_name SYMBOL,
            value DOUBLE,
            tags SYMBOL[]
        ) timestamp(ts) PARTITION BY DAY
    """)
    
    # Create test materialized views
    await dagster_resources.resources.materialize.execute("""
        CREATE MATERIALIZED VIEW test_event_counts AS
        SELECT
            toStartOfHour(timestamp) as hour,
            event_type,
            count(*) as event_count
        FROM test_events
        GROUP BY hour, event_type
    """)
    
    yield
    
    # Cleanup
    await dagster_resources.resources.clickhouse.execute("DROP TABLE IF EXISTS test_events")
    await dagster_resources.resources.questdb.execute("DROP TABLE IF EXISTS test_metrics")
    await dagster_resources.resources.materialize.execute("DROP VIEW IF EXISTS test_event_counts")

@pytest.fixture(scope="function")
async def sample_events(setup_test_tables, dagster_resources):
    """Provide sample test events."""
    test_events = [
        {
            "event_id": f"test-event-{i}",
            "timestamp": "2024-02-10T00:00:00",
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": '{"button_id": "submit", "page": "checkout"}',
            "context": '{"user_agent": "test-browser", "ip": "127.0.0.1"}'
        }
        for i in range(5)
    ]
    
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        test_events
    )
    
    yield test_events 