from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from typing import Optional, List
from .config import settings
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

def ensure_connection(func):
    """Decorator to ensure NATS connection before operation"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self._connected:
            await self.connect()
        return await func(self, *args, **kwargs)
    return wrapper

class NATSClient:
    """NATS client manager"""
    
    def __init__(self, servers: Optional[List[str]] = None):
        self._client: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._connected = False
        self._servers = servers or [settings.NATS_URL]
        self._subscriptions = []
    
    async def connect(self):
        """Connect to NATS server with retry logic"""
        if self._connected:
            return

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                self._client = NATS()
                # Extract token from URL if present
                server_url = self._servers[0]
                token = None
                if '@' in server_url:
                    # Parse URL to extract token
                    parts = server_url.split('@')
                    if len(parts) == 2:
                        token = parts[0].split('//')[1]
                        # Update server URL without token
                        server_url = f"nats://{parts[1]}"
                        self._servers[0] = server_url
                
                options = {
                    "servers": self._servers,
                    "connect_timeout": 5.0,
                    "max_reconnect_attempts": 3,
                    "reconnect_time_wait": 1.0,
                }
                
                if token:
                    options["token"] = token
                    logger.info("Using token authentication for NATS connection")
                
                await self._client.connect(**options)
                self._js = self._client.jetstream()
                self._connected = True
                logger.info("Connected to NATS")
                return
            except Exception as e:
                logger.warning(f"NATS connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("Failed to connect to NATS after all retries")
                    raise
    
    async def disconnect(self):
        """Disconnect from NATS"""
        if self._connected and self._client:
            try:
                # Unsubscribe from all subscriptions
                for sub in self._subscriptions:
                    await sub.unsubscribe()
                self._subscriptions.clear()
                
                # Drain the connection
                await self._client.drain()
                self._connected = False
                self._client = None
                self._js = None
                logger.info("Disconnected from NATS")
            except Exception as e:
                logger.error(f"Error during NATS disconnect: {str(e)}")
                raise
    
    def is_connected(self) -> bool:
        """Check if connected to NATS"""
        return self._connected and self._client and self._client.is_connected
    
    @ensure_connection
    async def publish(self, subject: str, payload: bytes):
        """Publish message to NATS"""
        await self._client.publish(subject, payload)
    
    @ensure_connection
    async def subscribe(self, subject: str, queue: str = "", cb=None):
        """Subscribe to NATS subject"""
        sub = await self._client.subscribe(subject, queue=queue, cb=cb)
        self._subscriptions.append(sub)
        return sub
    
    @ensure_connection
    async def request(self, subject: str, payload: bytes, timeout: float = 5.0):
        """Make request to NATS"""
        return await self._client.request(subject, payload, timeout=timeout)
    
    @property
    def jetstream(self) -> Optional[JetStreamContext]:
        """Get JetStream context"""
        return self._js
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

# Initialize default NATS client
nats_client = NATSClient() 