import pytest
from httpx import AsyncClient
from datetime import datetime
import uuid
from ..api.models.timeseries import EventData, MetricData

@pytest.mark.asyncio
async def test_ingest_events(client: AsyncClient, test_clickhouse, test_nats):
    """Test event ingestion endpoint"""
    events = [
        EventData(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            platform="web",
            event_type="user_interaction",
            event_name="button_click",
            properties={
                "button_id": "submit",
                "page": "checkout"
            },
            context={
                "user_agent": "Mozilla/5.0",
                "ip": "127.0.0.1"
            }
        )
    ]
    
    response = await client.post("/ingest/events", json=[e.dict() for e in events])
    assert response.status_code == 200
    assert response.json()["count"] == 1
    
    # Verify data in ClickHouse
    result = test_clickhouse.execute(
        "SELECT count() FROM user_interaction_events WHERE event_name = 'button_click'"
    )
    assert result[0][0] == 1

@pytest.mark.asyncio
async def test_ingest_metrics(client: AsyncClient, test_questdb):
    """Test metrics ingestion endpoint"""
    metrics = [
        MetricData(
            metric_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            name="api_latency",
            value=150.5,
            tags={
                "endpoint": "/api/users",
                "method": "GET"
            }
        )
    ]
    
    response = await client.post("/ingest/metrics", json=[m.dict() for m in metrics])
    assert response.status_code == 200
    assert response.json()["count"] == 1
    
    # Verify data in QuestDB
    result = test_questdb.execute(
        "SELECT count() FROM performance_events WHERE metric_name = 'api_latency'"
    )
    assert result[0][0] == 1

@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient):
    """Test rate limiting functionality"""
    # Create a batch of events that exceeds rate limit
    events = [
        EventData(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            platform="web",
            event_type="test",
            event_name="test_event"
        ) for _ in range(1100)  # Rate limit is 1000 per minute
    ]
    
    response = await client.post("/ingest/events", json=[e.dict() for e in events])
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]

@pytest.mark.asyncio
async def test_invalid_event_data(client: AsyncClient):
    """Test validation of invalid event data"""
    invalid_event = {
        "event_id": "not-a-uuid",
        "timestamp": "invalid-date",
        "platform": "web",
        "event_type": "test",
        "event_name": "test_event"
    }
    
    response = await client.post("/ingest/events", json=[invalid_event])
    assert response.status_code == 422
    
@pytest.mark.asyncio
async def test_batch_processing(client: AsyncClient, test_clickhouse, test_nats):
    """Test batch processing of events"""
    # Create a large batch of valid events
    events = [
        EventData(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            platform="web",
            event_type="user_interaction",
            event_name=f"test_event_{i}",
            properties={"index": i}
        ) for i in range(100)
    ]
    
    response = await client.post("/ingest/events", json=[e.dict() for e in events])
    assert response.status_code == 200
    assert response.json()["count"] == 100
    
    # Verify all events were processed
    result = test_clickhouse.execute(
        "SELECT count() FROM user_interaction_events WHERE event_type = 'user_interaction'"
    )
    assert result[0][0] == 100 