import pytest
from dagster import materialize_to_memory
from app.dagster.assets import events

@pytest.mark.asyncio
async def test_event_processing_assets(dagster_resources, setup_test_tables):
    """Test the complete event processing pipeline."""
    # Sample test event data
    test_events = [
        {
            "event_id": "test-event-1",
            "timestamp": "2024-02-10T00:00:00",
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": '{"button_id": "submit", "page": "checkout"}',
            "context": '{"user_agent": "test-browser", "ip": "127.0.0.1"}'
        }
    ]
    
    # Insert test data
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        test_events
    )
    
    # Run the asset materialization
    result = materialize_to_memory(
        [events.process_user_interactions],
        resources=dagster_resources.resources
    )
    
    # Verify the results
    assert result.success
    assert len(result.output_for_node("process_user_interactions")) > 0

@pytest.mark.asyncio
async def test_event_enrichment(dagster_resources, setup_test_tables):
    """Test the event enrichment process."""
    # Sample event for enrichment
    test_event = {
        "event_id": "test-event-2",
        "timestamp": "2024-02-10T00:00:00",
        "event_type": "performance",
        "event_name": "page_load",
        "properties": '{"load_time": 1.5, "page": "home"}',
        "context": '{"user_agent": "test-browser", "ip": "127.0.0.1"}'
    }
    
    # Insert test data
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        [test_event]
    )
    
    # Run the enrichment asset
    result = materialize_to_memory(
        [events.enrich_events],
        resources=dagster_resources.resources
    )
    
    # Verify enrichment
    assert result.success
    enriched_events = result.output_for_node("enrich_events")
    assert len(enriched_events) > 0
    assert "enriched_properties" in enriched_events[0]

@pytest.mark.asyncio
async def test_event_aggregation(dagster_resources, setup_test_tables):
    """Test event aggregation functionality."""
    # Insert multiple test events
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
    
    # Run the aggregation asset
    result = materialize_to_memory(
        [events.aggregate_events],
        resources=dagster_resources.resources
    )
    
    # Verify aggregation results
    assert result.success
    aggregations = result.output_for_node("aggregate_events")
    assert len(aggregations) > 0
    assert "event_count" in aggregations[0]
    assert aggregations[0]["event_count"] == 5 