import pytest
import logging
from pathlib import Path
import sys

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def test_data():
    """Fixture to provide test data for unit tests."""
    return {
        "sample_event": {
            "event_id": "test-event-1",
            "timestamp": "2024-02-10T00:00:00",
            "event_type": "user_interaction",
            "event_name": "button_click",
            "properties": {"button_id": "submit", "page": "checkout"},
            "context": {"user_agent": "test-browser", "ip": "127.0.0.1"}
        }
    } 