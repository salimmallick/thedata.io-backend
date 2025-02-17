import pytest
from dagster import build_sensor_context
from app.dagster.sensors.data_quality import (
    data_quality_sensor,
    schema_validation_sensor,
    data_freshness_sensor
)

@pytest.mark.asyncio
async def test_data_quality_sensor(dagster_resources, setup_test_tables):
    """Test the data quality monitoring sensor."""
    # Insert test data with quality issues
    test_events = [
        {
            "event_id": "test-event-1",
            "timestamp": "2024-02-10T00:00:00",
            "event_type": "user_interaction",
            "event_name": None,  # Invalid - should be string
            "properties": '{"button_id": "submit"}',
            "context": '{"user_agent": "test-browser"}'
        }
    ]
    
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        test_events
    )
    
    # Run the sensor
    context = build_sensor_context()
    result = data_quality_sensor(context)
    
    # Verify sensor detected quality issues
    assert result.run_requests is not None
    assert len(result.run_requests) > 0

@pytest.mark.asyncio
async def test_schema_validation_sensor(dagster_resources, setup_test_tables):
    """Test the schema validation sensor."""
    # Insert data with schema mismatch
    test_events = [
        {
            "event_id": "test-event-2",
            "timestamp": "invalid-timestamp",  # Invalid timestamp format
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": '{"button_id": 123}',  # Number instead of string
            "context": '{"user_agent": "test-browser"}'
        }
    ]
    
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        test_events
    )
    
    # Run the sensor
    context = build_sensor_context()
    result = schema_validation_sensor(context)
    
    # Verify schema validation issues were detected
    assert result.run_requests is not None
    assert len(result.run_requests) > 0

@pytest.mark.asyncio
async def test_data_freshness_sensor(dagster_resources, setup_test_tables):
    """Test the data freshness monitoring sensor."""
    # Insert old data
    old_events = [
        {
            "event_id": "test-event-3",
            "timestamp": "2023-01-01T00:00:00",  # Old timestamp
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": '{"button_id": "submit"}',
            "context": '{"user_agent": "test-browser"}'
        }
    ]
    
    await dagster_resources.resources.clickhouse.execute(
        "INSERT INTO test_events FORMAT JSONEachRow",
        old_events
    )
    
    # Run the sensor
    context = build_sensor_context()
    result = data_freshness_sensor(context)
    
    # Verify freshness issues were detected
    assert result.run_requests is not None
    assert len(result.run_requests) > 0
    
    # Verify sensor metadata
    assert "last_event_timestamp" in result.cursor
    assert "stale_tables" in result.cursor 