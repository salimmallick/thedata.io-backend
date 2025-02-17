from datetime import datetime
from typing import Dict, Any, Optional, Callable
import json

class EventValidationError(Exception):
    """Custom exception for event validation errors."""
    pass

def validate_event(event: Dict[str, Any]) -> None:
    """Validate an event against required schema and rules."""
    required_fields = ["event_id", "timestamp", "event_type", "event_name"]
    
    # Check required fields
    missing_fields = [field for field in required_fields if field not in event]
    if missing_fields:
        raise EventValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate timestamp format
    try:
        if isinstance(event["timestamp"], str):
            datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
    except (ValueError, TypeError):
        raise EventValidationError("Invalid timestamp format")
    
    # Validate properties is a dictionary
    if "properties" in event and not isinstance(event["properties"], dict):
        raise EventValidationError("Properties must be a dictionary")
    
    # Validate context is a dictionary if present
    if "context" in event and not isinstance(event["context"], dict):
        raise EventValidationError("Context must be a dictionary")

def transform_event(
    event: Dict[str, Any],
    enrich: bool = False,
    custom_transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Transform and optionally enrich an event."""
    # Create a copy to avoid modifying the original
    transformed = event.copy()
    
    # Convert timestamp to datetime if it's a string
    if isinstance(transformed["timestamp"], str):
        transformed["timestamp"] = datetime.fromisoformat(
            transformed["timestamp"].replace('Z', '+00:00')
        )
    
    # Add processing timestamp
    transformed["processed_at"] = datetime.utcnow()
    
    # Apply enrichment if requested
    if enrich:
        transformed["enriched_properties"] = enrich_event_data(transformed)
    
    # Apply custom transformation if provided
    if custom_transform:
        transformed = custom_transform(transformed)
    
    return transformed

def enrich_event_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich event data with additional context and derived fields."""
    enriched = {}
    
    # Extract and derive categories
    if "properties" in event:
        props = event["properties"]
        if "category" in props:
            enriched["derived_category"] = props["category"]
            enriched["product_category"] = props["category"]
    
    # Add device information if available
    if "context" in event and "user_agent" in event["context"]:
        enriched["device_info"] = extract_device_info(event["context"]["user_agent"])
    
    # Add geo information if IP is available
    if "context" in event and "ip" in event["context"]:
        enriched["geo_info"] = get_geo_info(event["context"]["ip"])
    
    return enriched

def extract_device_info(user_agent: str) -> Dict[str, str]:
    """Extract device information from user agent string."""
    # Simple extraction - in production, use a proper user agent parser
    info = {
        "device_type": "unknown",
        "browser": "unknown",
        "os": "unknown"
    }
    
    user_agent = user_agent.lower()
    
    # Basic device type detection
    if "mobile" in user_agent:
        info["device_type"] = "mobile"
    elif "tablet" in user_agent:
        info["device_type"] = "tablet"
    else:
        info["device_type"] = "desktop"
    
    # Basic browser detection
    browsers = ["chrome", "firefox", "safari", "edge"]
    for browser in browsers:
        if browser in user_agent:
            info["browser"] = browser
            break
    
    # Basic OS detection
    os_list = {"windows": "Windows", "mac": "MacOS", "linux": "Linux", "android": "Android", "ios": "iOS"}
    for os_key, os_name in os_list.items():
        if os_key in user_agent:
            info["os"] = os_name
            break
    
    return info

def get_geo_info(ip: str) -> Dict[str, str]:
    """Get geographical information from IP address."""
    # In production, use a proper IP geolocation service
    # This is a mock implementation
    return {
        "country": "Unknown",
        "region": "Unknown",
        "city": "Unknown",
        "latitude": "0",
        "longitude": "0"
    } 