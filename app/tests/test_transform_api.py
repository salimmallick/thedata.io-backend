import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.api.core.transform import TransformationType
from app.api.core.config.transform_config import config_manager
from app.main import app

@pytest.fixture
def test_client():
    """Create a test client"""
    return TestClient(app)

@pytest.fixture
def mock_token():
    """Mock an admin token"""
    return {"permissions": ["manage_transformations"]}

@pytest.fixture
def test_rule_data():
    """Test rule data"""
    return {
        "name": "test_rule",
        "type": TransformationType.ENRICH,
        "enabled": True,
        "order": 1,
        "config": {
            "test_key": "test_value"
        }
    }

def test_list_rules(test_client, mock_token):
    """Test listing transformation rules"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        response = test_client.get("/transform/rules")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

def test_get_rule(test_client, mock_token, test_rule_data):
    """Test getting a specific rule"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        # First create a rule
        response = test_client.post("/transform/rules", json=test_rule_data)
        assert response.status_code == 200
        
        # Then get it
        response = test_client.get(f"/transform/rules/{test_rule_data['name']}")
        assert response.status_code == 200
        rule = response.json()
        assert rule["name"] == test_rule_data["name"]
        assert rule["type"] == test_rule_data["type"]
        assert rule["config"] == test_rule_data["config"]

def test_create_rule(test_client, mock_token, test_rule_data):
    """Test creating a new rule"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        response = test_client.post("/transform/rules", json=test_rule_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify rule was created
        config = config_manager.get_rule_config(test_rule_data["name"])
        assert config is not None
        assert config.name == test_rule_data["name"]
        assert config.type == test_rule_data["type"]
        assert config.config == test_rule_data["config"]

def test_update_rule(test_client, mock_token, test_rule_data):
    """Test updating a rule"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        # First create a rule
        response = test_client.post("/transform/rules", json=test_rule_data)
        assert response.status_code == 200
        
        # Update the rule
        updates = {
            "enabled": False,
            "config": {"new_key": "new_value"}
        }
        response = test_client.patch(
            f"/transform/rules/{test_rule_data['name']}",
            json=updates
        )
        assert response.status_code == 200
        
        # Verify updates
        config = config_manager.get_rule_config(test_rule_data["name"])
        assert config.enabled == updates["enabled"]
        assert config.config == updates["config"]

def test_delete_rule(test_client, mock_token, test_rule_data):
    """Test deleting a rule"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        # First create a rule
        response = test_client.post("/transform/rules", json=test_rule_data)
        assert response.status_code == 200
        
        # Delete the rule
        response = test_client.delete(f"/transform/rules/{test_rule_data['name']}")
        assert response.status_code == 200
        
        # Verify rule was deleted
        config = config_manager.get_rule_config(test_rule_data["name"])
        assert config is None

def test_toggle_rule(test_client, mock_token, test_rule_data):
    """Test toggling a rule's enabled status"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        # First create a rule
        response = test_client.post("/transform/rules", json=test_rule_data)
        assert response.status_code == 200
        
        # Toggle the rule
        response = test_client.post(f"/transform/rules/{test_rule_data['name']}/toggle")
        assert response.status_code == 200
        
        # Verify rule was toggled
        config = config_manager.get_rule_config(test_rule_data["name"])
        assert config.enabled == False  # Should be toggled from True to False

def test_unauthorized_access(test_client):
    """Test unauthorized access to endpoints"""
    # Mock token without required permissions
    mock_unauth_token = {"permissions": []}
    
    with patch("app.api.core.security.get_current_user_token", return_value=mock_unauth_token):
        endpoints = [
            ("GET", "/transform/rules"),
            ("POST", "/transform/rules"),
            ("GET", "/transform/rules/test"),
            ("PATCH", "/transform/rules/test"),
            ("DELETE", "/transform/rules/test"),
            ("POST", "/transform/rules/test/toggle")
        ]
        
        for method, endpoint in endpoints:
            response = test_client.request(method, endpoint)
            assert response.status_code == 403

def test_invalid_rule_creation(test_client, mock_token):
    """Test creating a rule with invalid data"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        # Test with unknown rule type
        invalid_rule = {
            "name": "invalid_rule",
            "type": "UNKNOWN_TYPE",
            "enabled": True,
            "order": 1,
            "config": {}
        }
        response = test_client.post("/transform/rules", json=invalid_rule)
        assert response.status_code == 422  # Validation error

def test_rule_not_found(test_client, mock_token):
    """Test operations on non-existent rules"""
    with patch("app.api.core.security.get_current_user_token", return_value=mock_token):
        rule_name = "nonexistent_rule"
        
        # Test get
        response = test_client.get(f"/transform/rules/{rule_name}")
        assert response.status_code == 404
        
        # Test update
        response = test_client.patch(
            f"/transform/rules/{rule_name}",
            json={"enabled": False}
        )
        assert response.status_code == 404
        
        # Test delete
        response = test_client.delete(f"/transform/rules/{rule_name}")
        assert response.status_code == 404
        
        # Test toggle
        response = test_client.post(f"/transform/rules/{rule_name}/toggle")
        assert response.status_code == 404 