import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nats.aio.client import Client as NATS
from app.api.core.nats import NATSClient

@pytest.mark.asyncio
async def test_nats_client_init():
    """Test NATSClient initialization."""
    client = NATSClient(servers=["nats://localhost:4222"])
    assert client._servers == ["nats://localhost:4222"]
    assert not client._connected
    assert client._client is None

@pytest.mark.asyncio
async def test_nats_client_connect():
    """Test NATSClient connect method."""
    with patch('app.api.core.nats.NATS') as mock_nats:
        # Setup mock
        mock_instance = AsyncMock()
        mock_nats.return_value = mock_instance
        mock_instance.connect = AsyncMock()
        mock_instance.jetstream = MagicMock()
        
        # Test connection
        client = NATSClient(["nats://localhost:4222"])
        await client.connect()
        
        # Verify
        assert client._connected
        mock_instance.connect.assert_called_once()
        assert client._client is not None

@pytest.mark.asyncio
async def test_nats_client_disconnect():
    """Test NATSClient disconnect method."""
    with patch('app.api.core.nats.NATS') as mock_nats:
        # Setup mock
        mock_instance = AsyncMock()
        mock_nats.return_value = mock_instance
        mock_instance.drain = AsyncMock()
        
        # Test disconnection
        client = NATSClient(["nats://localhost:4222"])
        client._connected = True
        client._client = mock_instance
        
        await client.disconnect()
        
        # Verify
        assert not client._connected
        mock_instance.drain.assert_called_once()
        assert client._client is None

@pytest.mark.asyncio
async def test_nats_client_publish():
    """Test NATSClient publish method."""
    with patch('app.api.core.nats.NATS') as mock_nats:
        # Setup mock
        mock_instance = AsyncMock()
        mock_nats.return_value = mock_instance
        mock_instance.publish = AsyncMock()
        
        # Test publishing
        client = NATSClient(["nats://localhost:4222"])
        client._connected = True
        client._client = mock_instance
        
        test_subject = "test.subject"
        test_payload = b"test message"
        await client.publish(test_subject, test_payload)
        
        # Verify
        mock_instance.publish.assert_called_once_with(test_subject, test_payload)

@pytest.mark.asyncio
async def test_nats_client_subscribe():
    """Test NATSClient subscribe method."""
    with patch('app.api.core.nats.NATS') as mock_nats:
        # Setup mock
        mock_instance = AsyncMock()
        mock_nats.return_value = mock_instance
        mock_instance.subscribe = AsyncMock()
        
        # Test subscription
        client = NATSClient(["nats://localhost:4222"])
        client._connected = True
        client._client = mock_instance
        
        test_subject = "test.subject"
        test_queue = "test_queue"
        test_callback = AsyncMock()
        
        await client.subscribe(test_subject, test_queue, test_callback)
        
        # Verify
        mock_instance.subscribe.assert_called_once_with(
            test_subject,
            queue=test_queue,
            cb=test_callback
        ) 