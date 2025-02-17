import pytest
import asyncio
import logging
from nats.aio.client import Client as NATS
from app.api.core.nats import NATSClient

logger = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nats_basic_pubsub(nats_client: NATS):
    """Test basic NATS publish/subscribe functionality."""
    future = asyncio.Future()
    
    # Subscribe first
    logger.info("Setting up subscription...")
    async def message_handler(msg):
        logger.info(f"Received message: {msg.data.decode()}")
        future.set_result(msg.data.decode())
    
    async with nats_client as nc:
        sub = await nc.subscribe("test.subject", cb=message_handler)
        
        # Publish message
        test_message = "Hello NATS!"
        await nc.publish("test.subject", test_message.encode())
        
        # Wait for message
        try:
            received = await asyncio.wait_for(future, timeout=5.0)
            assert received == test_message
        finally:
            await sub.unsubscribe()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nats_queue_group(nats_client: NATS):
    """Test NATS queue group functionality."""
    received_messages = []
    message_count = 5
    subscriber_count = 3
    
    async with nats_client as nc:
        # Create multiple subscribers in the same queue group
        subs = []
        for i in range(subscriber_count):
            async def message_handler(msg, subscriber_id=i):
                message = msg.data.decode()
                logger.info(f"Subscriber {subscriber_id} received: {message}")
                received_messages.append((subscriber_id, message))
            
            sub = await nc.subscribe(
                "test.queue",
                queue="test_group",
                cb=message_handler
            )
            subs.append(sub)
        
        # Publish messages
        for i in range(message_count):
            await nc.publish("test.queue", f"Message {i}".encode())
        
        # Wait for messages to be processed
        await asyncio.sleep(1)
        
        try:
            # Verify message distribution
            assert len(received_messages) == message_count
            # Verify messages were distributed across subscribers
            subscriber_counts = [0] * subscriber_count
            for sub_id, _ in received_messages:
                subscriber_counts[sub_id] += 1
            # Check that at least one subscriber got a message
            assert any(count > 0 for count in subscriber_counts)
        finally:
            for sub in subs:
                await sub.unsubscribe()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nats_request_reply(nats_client: NATS):
    """Test NATS request-reply pattern."""
    async with nats_client as nc:
        # Setup reply handler
        async def reply_handler(msg):
            response = f"Reply to: {msg.data.decode()}"
            await nc.publish(msg.reply, response.encode())
        
        sub = await nc.subscribe("test.service", cb=reply_handler)
        
        try:
            # Send request and wait for reply
            response = await nc.request("test.service", b"Hello Service!", timeout=5.0)
            assert response.data.decode().startswith("Reply to: Hello Service!")
        finally:
            await sub.unsubscribe()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nats_client_wrapper():
    """Test the NATSClient wrapper class."""
    client = NATSClient(["nats://nats-test:4222"])
    
    try:
        # Test connection
        await client.connect()
        assert client.is_connected()
        
        # Test pub/sub
        future = asyncio.Future()
        async def message_handler(msg):
            future.set_result(msg.data.decode())
        
        await client.subscribe("test.wrapper", cb=message_handler)
        await client.publish("test.wrapper", b"Test wrapper")
        
        # Wait for message
        received = await asyncio.wait_for(future, timeout=5.0)
        assert received == "Test wrapper"
        
    finally:
        await client.disconnect()
        assert not client.is_connected() 