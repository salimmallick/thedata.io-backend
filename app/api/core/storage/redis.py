from typing import Optional, Any, Dict, List, Set
import redis.asyncio as redis_async
import json
import logging
import asyncio
from ..config import settings

logger = logging.getLogger(__name__)

class RedisManager:
    """Manager for Redis connections"""
    
    def __init__(self):
        self._redis = None
        self._connected = False
        self._max_retries = 3
        self._retry_delay = 1  # seconds
    
    async def connect(self):
        """Connect to Redis"""
        if not self._connected:
            retries = 0
            while retries < self._max_retries:
                try:
                    self._redis = await redis_async.from_url(
                        settings.REDIS_URL,
                        encoding="utf-8",
                        decode_responses=True,
                        retry_on_timeout=True,
                        health_check_interval=30
                    )
                    self._connected = True
                    logger.info("Connected to Redis")
                    break
                except Exception as e:
                    retries += 1
                    if retries == self._max_retries:
                        logger.error(f"Redis connection error: {str(e)}")
                        raise
                    logger.warning(f"Redis connection attempt {retries} failed, retrying...")
                    await asyncio.sleep(self._retry_delay)
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._connected and self._redis:
            try:
                await self._redis.aclose()
            except Exception as e:
                logger.error(f"Redis disconnect error: {str(e)}")
            finally:
                self._connected = False
                logger.info("Disconnected from Redis")
    
    async def _ensure_connection(self):
        """Ensure Redis connection is active"""
        if not self._connected:
            await self.connect()
        try:
            await self._redis.ping()
        except:
            self._connected = False
            await self.connect()
    
    async def _execute_with_retry(self, operation):
        """Execute Redis operation with retry logic"""
        retries = 0
        while retries < self._max_retries:
            try:
                await self._ensure_connection()
                return await operation()
            except Exception as e:
                retries += 1
                if retries == self._max_retries:
                    raise
                logger.warning(f"Redis operation failed, attempt {retries}, retrying...")
                await asyncio.sleep(self._retry_delay)
                self._connected = False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        return await self._execute_with_retry(
            lambda: self._redis.get(key)
        )
    
    async def set(self, key: str, value: str, ex: int = None):
        """Set value in Redis with optional expiration"""
        await self._execute_with_retry(
            lambda: self._redis.set(key, value, ex=ex)
        )
    
    async def delete(self, key: str):
        """Delete key from Redis"""
        await self._execute_with_retry(
            lambda: self._redis.delete(key)
        )
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self._execute_with_retry(
            lambda: self._redis.exists(key)
        )
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        return await self._execute_with_retry(
            lambda: self._redis.keys(pattern)
        )
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key"""
        return await self._execute_with_retry(
            lambda: self._redis.ttl(key)
        )
    
    async def sadd(self, key: str, member: str):
        """Add member to set"""
        await self._execute_with_retry(
            lambda: self._redis.sadd(key, member)
        )
    
    async def srem(self, key: str, member: str):
        """Remove member from set"""
        await self._execute_with_retry(
            lambda: self._redis.srem(key, member)
        )
    
    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set"""
        return await self._execute_with_retry(
            lambda: self._redis.smembers(key)
        )
    
    async def info(self, section: str = None) -> Dict[str, Any]:
        """Get Redis server info"""
        return await self._execute_with_retry(
            lambda: self._redis.info(section)
        )

    async def ping(self):
        """Ping Redis to check connection."""
        try:
            await self._ensure_connection()
            await self._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False

    async def set_cache(self, key: str, value: str, ex: int = None):
        """Set a value in the cache with optional expiration."""
        try:
            await self._ensure_connection()
            await self._redis.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis set_cache failed: {str(e)}")
            return False

# Initialize Redis manager
redis = RedisManager()

class RedisService:
    """Redis service for caching and rate limiting"""
    
    def __init__(self):
        self._redis: Optional[redis_async.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        if not self._connected:
            self._redis = await redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self._connected = True
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._connected and self._redis:
            await self._redis.close()
            self._connected = False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            await self.connect()
        
        value = await self._redis.get(f"cache:{key}")
        if value:
            return json.loads(value)
        return None
    
    async def set_cache(
        self,
        key: str,
        value: Any,
        ex: int = 300  # 5 minutes default
    ):
        """Set value in cache with expiration"""
        if not self._connected:
            await self.connect()
        
        await self._redis.set(
            f"cache:{key}",
            json.dumps(value),
            ex=ex
        )
    
    async def invalidate_cache(self, key: str):
        """Remove key from cache"""
        if not self._connected:
            await self.connect()
        
        await self._redis.delete(f"cache:{key}")
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int = 60  # 1 minute default
    ) -> bool:
        """Check if rate limit is exceeded"""
        if not self._connected:
            await self.connect()
        
        # Get current timestamp for the window
        now = int(time.time())
        window_key = f"ratelimit:{key}:{now // window}"
        
        # Use pipeline for atomic operations
        async with self._redis.pipeline() as pipe:
            # Get current count and increment
            await pipe.incr(window_key)
            # Set expiration if not already set
            await pipe.expire(window_key, window)
            # Execute pipeline
            current_count, _ = await pipe.execute()
        
        return current_count <= limit
    
    async def get_rate_limit_info(
        self,
        key: str,
        window: int = 60
    ) -> Dict[str, int]:
        """Get rate limit information"""
        if not self._connected:
            await self.connect()
        
        now = int(time.time())
        window_key = f"ratelimit:{key}:{now // window}"
        
        count = await self._redis.get(window_key)
        ttl = await self._redis.ttl(window_key)
        
        return {
            "count": int(count) if count else 0,
            "ttl": max(0, ttl)
        }

# Create global Redis service instance
redis_service = RedisService() 