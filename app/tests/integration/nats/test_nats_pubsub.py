import pytest
import asyncio
import logging
from nats.aio.client import Client as NATS

logger = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nats_pubsub(nats_client: NATS):
    """Test NATS pub/sub functionality using the fixture."""
    future = asyncio.Future()
    
    # Subscribe first
    logger.info("Setting up subscription...")
    async def message_handler(msg):
        logger.info(f"Received message: {msg.data.decode()}")
        future.set_result(msg.data.decode())
    
    sub = await nats_client.subscribe("test.subject", cb=message_handler)
    logger.info("Subscription created")
    
    # Then publish
    test_message = "Hello NATS!"
    logger.info(f"Publishing message: {test_message}")
    await nats_client.publish("test.subject", test_message.encode())
    logger.info("Message published")
    
    # Wait for the message
    try:
        received = await asyncio.wait_for(future, timeout=5.0)
        logger.info(f"Received message successfully: {received}")
        assert received == test_message
        logger.info("Test passed!")
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for message!")
        raise
    finally:
        await sub.unsubscribe() 