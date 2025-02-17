from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

class EventValidationError(Exception):
    """Custom exception for event validation errors."""
    pass

class Event(BaseModel):
    """Event model for validation."""
    event_id: str = Field(..., description="Unique identifier for the event")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    event_type: str = Field(..., description="Type of event")
    event_name: str = Field(..., description="Name of the event")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Event properties")

    @validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError("Invalid timestamp format. Expected ISO 8601 format.")

def validate_event(event_data: Dict[str, Any]) -> None:
    """Validate a single event."""
    try:
        Event(**event_data)
    except Exception as e:
        missing_fields = []
        if "event_id" not in event_data:
            missing_fields.append("event_id")
        if "timestamp" not in event_data:
            missing_fields.append("timestamp")
        if "event_type" not in event_data:
            missing_fields.append("event_type")
        if "event_name" not in event_data:
            missing_fields.append("event_name")
        
        if missing_fields:
            raise EventValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        raise EventValidationError(str(e))

def validate_batch_events(events: List[Dict[str, Any]]) -> None:
    """Validate multiple events in a batch."""
    errors = []
    for i, event in enumerate(events):
        try:
            validate_event(event)
        except EventValidationError as e:
            errors.append(f"Event {event.get('event_id', f'at index {i}')} validation failed: {str(e)}")
    
    if errors:
        raise EventValidationError("\n".join(errors))

def transform_event(event_data: Dict[str, Any], enrichment_rules: Dict[str, Any] = None) -> Dict[str, Any]:
    """Transform and enrich event data."""
    # Validate event first
    validate_event(event_data)
    
    # Create a copy to avoid modifying the original
    transformed = event_data.copy()
    
    # Add standard enrichments
    transformed["processed_at"] = datetime.utcnow().isoformat()
    
    # Apply custom enrichment rules if provided
    if enrichment_rules:
        for field, rule in enrichment_rules.items():
            if callable(rule):
                transformed[field] = rule(transformed)
            else:
                transformed[field] = rule
    
    return transformed

class EventValidator:
    """Validator for event data and processing"""
    
    def __init__(self):
        self.validation_thresholds = {
            "batch_size": 1000,  # Maximum events in a batch
            "field_length": 1024,  # Maximum field length
            "max_properties": 50   # Maximum number of properties
        }
    
    async def validate_event(self, event_data: Dict[str, Any]) -> None:
        """Validate a single event with enhanced checks"""
        try:
            # Basic validation
            validate_event(event_data)
            
            # Additional validations
            await self._validate_field_lengths(event_data)
            await self._validate_properties(event_data)
            
        except EventValidationError as e:
            logger.error(f"Event validation failed: {str(e)}")
            raise
    
    async def validate_batch(self, events: List[Dict[str, Any]]) -> None:
        """Validate a batch of events"""
        if len(events) > self.validation_thresholds["batch_size"]:
            raise EventValidationError(
                f"Batch size exceeds maximum of {self.validation_thresholds['batch_size']} events"
            )
        
        validate_batch_events(events)
    
    async def transform_event(
        self,
        event_data: Dict[str, Any],
        enrichment_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Transform and validate an event"""
        # Validate first
        await self.validate_event(event_data)
        
        # Then transform
        return transform_event(event_data, enrichment_rules)
    
    async def _validate_field_lengths(self, event_data: Dict[str, Any]) -> None:
        """Validate field lengths"""
        for field, value in event_data.items():
            if isinstance(value, str) and len(value) > self.validation_thresholds["field_length"]:
                raise EventValidationError(
                    f"Field '{field}' exceeds maximum length of {self.validation_thresholds['field_length']} characters"
                )
    
    async def _validate_properties(self, event_data: Dict[str, Any]) -> None:
        """Validate event properties"""
        properties = event_data.get("properties", {})
        if len(properties) > self.validation_thresholds["max_properties"]:
            raise EventValidationError(
                f"Number of properties exceeds maximum of {self.validation_thresholds['max_properties']}"
            )

# Create global event validator instance
event_validator = EventValidator() 