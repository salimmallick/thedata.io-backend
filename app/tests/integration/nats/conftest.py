import pytest
import asyncio
import logging
import os
from typing import AsyncGenerator
from nats.aio.client import Client as NATS

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
async def nats_client() -> AsyncGenerator[NATS, None]:
    """Fixture to provide a NATS client for tests."""
    nc = NATS()
    nats_url = os.environ.get("NATS_URL", "nats://nats-test:4222")
    
    try:
        logger.info(f"Connecting to NATS at {nats_url}...")
        await nc.connect(
            servers=[nats_url],
            connect_timeout=5.0,
            max_reconnect_attempts=3,
            name="test-client"
        )
        logger.info("Connected to NATS successfully")
        yield nc
    finally:
        logger.info("Cleaning up NATS connection...")
        try:
            await nc.drain()
            await nc.close()
        except Exception as e:
            logger.error(f"Error during NATS cleanup: {e}")
        logger.info("NATS cleanup complete") 