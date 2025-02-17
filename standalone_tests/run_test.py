import asyncio
from nats.aio.client import Client as NATS
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Disable other loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

async def test_nats():
    """Test NATS connection and pub/sub without any dependencies."""
    logger.info("Starting NATS test")
    
    # Create NATS client
    nc = NATS()
    
    try:
        # Connect with debug info
        nats_url = os.environ.get("NATS_URL", "nats://nats-test:4222")
        logger.info(f"Attempting to connect to NATS at {nats_url}...")
        
        await nc.connect(
            servers=[nats_url],
            connect_timeout=5.0,
            max_reconnect_attempts=0,
            name="test-client"
        )
        logger.info("Connected to NATS successfully")
        
        # Create a future to wait for the message
        future = asyncio.Future()
        
        # Subscribe first
        logger.info("Setting up subscription...")
        async def message_handler(msg):
            logger.info(f"Received message: {msg.data.decode()}")
            future.set_result(msg.data.decode())
        
        sub = await nc.subscribe("test.subject", cb=message_handler)
        logger.info("Subscription created")
        
        # Then publish
        test_message = "Hello NATS!"
        logger.info(f"Publishing message: {test_message}")
        await nc.publish("test.subject", test_message.encode())
        logger.info("Message published")
        
        # Wait for the message
        logger.info("Waiting for message...")
        try:
            received = await asyncio.wait_for(future, timeout=5.0)
            logger.info(f"Received message successfully: {received}")
            assert received == test_message
            logger.info("Test passed!")
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for message!")
            raise
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        try:
            await nc.drain()
            await nc.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        logger.info("Cleanup complete")

if __name__ == "__main__":
    asyncio.run(test_nats()) 