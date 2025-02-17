import pytest
from datetime import datetime
from app.api.core.event_validation import (
    validate_event,
    validate_batch_events,
    transform_event,
    EventValidationError
)

def test_validate_event_basic():
    """Test basic event validation."""
    event = {
        "event_id": "test-123",
        "timestamp": "2024-02-10T00:00:00Z",
        "event_type": "user_interaction",
        "event_name": "button_click",
        "properties": {"button_id": "submit"}
    }
    validate_event(event)  # Should not raise any exception

def test_validate_event_missing_required():
    """Test validation with missing required fields."""
    event = {
        "event_type": "user_interaction",
        "properties": {}
    }
    with pytest.raises(EventValidationError) as exc_info:
        validate_event(event)
    assert "Missing required fields" in str(exc_info.value)
    assert "event_id" in str(exc_info.value)
    assert "timestamp" in str(exc_info.value)
    assert "event_name" in str(exc_info.value)

def test_validate_event_invalid_timestamp():
    """Test validation with invalid timestamp format."""
    event = {
        "event_id": "test-123",
        "timestamp": "invalid-timestamp",
        "event_type": "user_interaction",
        "event_name": "button_click",
        "properties": {}
    }
    with pytest.raises(EventValidationError) as exc_info:
        validate_event(event)
    assert "Invalid timestamp format" in str(exc_info.value)

def test_validate_event_invalid_properties():
    """Test validation with invalid properties type."""
    event = {
        "event_id": "test-123",
        "timestamp": "2024-02-10T00:00:00Z",
        "event_type": "user_interaction",
        "event_name": "button_click",
        "properties": "invalid"  # Should be a dict
    }
    with pytest.raises(EventValidationError) as exc_info:
        validate_event(event)
    assert "properties" in str(exc_info.value)

def test_transform_event():
    """Test basic event transformation."""
    event = {
        "event_id": "test-123",
        "timestamp": "2024-02-10T00:00:00Z",
        "event_type": "user_interaction",
        "event_name": "button_click",
        "properties": {"button_id": "submit"}
    }
    transformed = transform_event(event)
    assert transformed["event_id"] == event["event_id"]
    assert transformed["timestamp"] == event["timestamp"]
    assert transformed["event_type"] == event["event_type"]
    assert transformed["event_name"] == event["event_name"]
    assert transformed["properties"] == event["properties"]
    assert "processed_at" in transformed

def test_transform_event_with_enrichment():
    """Test event transformation with enrichment rules."""
    event = {
        "event_id": "test-123",
        "timestamp": "2024-02-10T00:00:00Z",
        "event_type": "user_interaction",
        "event_name": "button_click",
        "properties": {"button_id": "submit"}
    }
    enrichment_rules = {
        "environment": "test",
        "version": lambda e: "1.0"
    }
    transformed = transform_event(event, enrichment_rules)
    assert transformed["environment"] == "test"
    assert transformed["version"] == "1.0"

def test_transform_event_with_custom_rules():
    """Test event transformation with custom enrichment rules."""
    event = {
        "event_id": "test-123",
        "timestamp": "2024-02-10T00:00:00Z",
        "event_type": "user_interaction",
        "event_name": "button_click",
        "properties": {"button_id": "submit"}
    }
    def custom_enrichment(event):
        return f"{event['event_type']}_{event['event_name']}"
    
    enrichment_rules = {
        "event_key": custom_enrichment
    }
    transformed = transform_event(event, enrichment_rules)
    assert transformed["event_key"] == "user_interaction_button_click"

def test_validate_batch_events():
    """Test validation of multiple events in a batch."""
    events = [
        {
            "event_id": f"test-{i}",
            "timestamp": "2024-02-10T00:00:00Z",
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": {"index": i}
        }
        for i in range(3)
    ]
    # Add one invalid event
    events.append({
        "event_id": "test-invalid",
        "event_type": "invalid"  # Missing required fields
    })

    # Should raise exception with details about the invalid event
    with pytest.raises(EventValidationError) as exc_info:
        validate_batch_events(events)
    assert "test-invalid" in str(exc_info.value)
    assert "Missing required fields" in str(exc_info.value) 