import pytest
from httpx import AsyncClient
import hmac
import hashlib
import time
import json
from ..api.core.security import security
from ..api.models.organization import Organization

@pytest.fixture
async def test_org(test_postgres):
    """Create a test organization"""
    org_data = {
        "name": "Test Org",
        "api_key": "test_key_123",
        "api_secret": "test_secret_456",
        "tier": "basic"
    }
    
    await test_postgres.execute(
        """
        INSERT INTO organizations (name, api_key, api_secret, tier)
        VALUES ($1, $2, $3, $4)
        """,
        org_data["name"],
        org_data["api_key"],
        org_data["api_secret"],
        org_data["tier"]
    )
    
    return Organization(**org_data)

def generate_signature(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    """Generate request signature"""
    message = f"{timestamp}{method}{path}{body}"
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

@pytest.mark.asyncio
async def test_api_key_validation(client: AsyncClient, test_org):
    """Test API key validation"""
    # Valid API key
    response = await client.get(
        "/health",
        headers={"X-API-Key": test_org.api_key}
    )
    assert response.status_code == 200
    
    # Invalid API key
    response = await client.get(
        "/health",
        headers={"X-API-Key": "invalid_key"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_request_signing(client: AsyncClient, test_org):
    """Test request signature validation"""
    timestamp = str(int(time.time()))
    path = "/ingest/events"
    method = "POST"
    body = json.dumps([{
        "event_type": "test",
        "event_name": "test_event"
    }])
    
    # Valid signature
    signature = generate_signature(
        test_org.api_secret,
        timestamp,
        method,
        path,
        body
    )
    
    response = await client.post(
        path,
        content=body,
        headers={
            "X-API-Key": test_org.api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp
        }
    )
    assert response.status_code == 200
    
    # Invalid signature
    response = await client.post(
        path,
        content=body,
        headers={
            "X-API-Key": test_org.api_key,
            "X-Signature": "invalid_signature",
            "X-Timestamp": timestamp
        }
    )
    assert response.status_code == 401
    
    # Old timestamp
    old_timestamp = str(int(time.time()) - 600)  # 10 minutes old
    old_signature = generate_signature(
        test_org.api_secret,
        old_timestamp,
        method,
        path,
        body
    )
    
    response = await client.post(
        path,
        content=body,
        headers={
            "X-API-Key": test_org.api_key,
            "X-Signature": old_signature,
            "X-Timestamp": old_timestamp
        }
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_security_headers(client: AsyncClient):
    """Test security headers are present"""
    response = await client.get("/health")
    
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers

@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient, test_org):
    """Test rate limiting"""
    # Make requests up to the limit
    timestamp = str(int(time.time()))
    path = "/ingest/events"
    method = "POST"
    body = json.dumps([{"event_type": "test"}])
    signature = generate_signature(
        test_org.api_secret,
        timestamp,
        method,
        path,
        body
    )
    
    headers = {
        "X-API-Key": test_org.api_key,
        "X-Signature": signature,
        "X-Timestamp": timestamp
    }
    
    # Basic tier limit is 5000 requests per minute
    for _ in range(5000):
        response = await client.post(path, content=body, headers=headers)
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = await client.post(path, content=body, headers=headers)
    assert response.status_code == 429
    assert "Retry-After" in response.headers

@pytest.mark.asyncio
async def test_audit_logging(client: AsyncClient, test_org, tmp_path):
    """Test audit logging"""
    # Configure audit log path
    import logging
    audit_log_path = tmp_path / "audit.log"
    handler = logging.FileHandler(audit_log_path)
    security.audit_logger.addHandler(handler)
    
    # Make a request
    timestamp = str(int(time.time()))
    path = "/ingest/events"
    method = "POST"
    body = json.dumps([{"event_type": "test"}])
    signature = generate_signature(
        test_org.api_secret,
        timestamp,
        method,
        path,
        body
    )
    
    response = await client.post(
        path,
        content=body,
        headers={
            "X-API-Key": test_org.api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp
        }
    )
    assert response.status_code == 200
    
    # Verify audit log
    with open(audit_log_path) as f:
        log_entry = json.loads(f.read().strip())
        assert log_entry["organization_id"] == test_org.id
        assert log_entry["method"] == method
        assert log_entry["path"] == path
        assert log_entry["response_status"] == 200 