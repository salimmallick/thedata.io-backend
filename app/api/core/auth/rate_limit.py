from typing import Dict, Any, Optional
import time
import logging
from ..config import settings
from ..storage.redis import redis_service
from ..monitoring.metrics import metrics

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self):
        self.rate_limits = {
            "default": {
                "limit": 100,
                "window": 60  # 1 minute
            },
            "high_frequency": {
                "limit": 1000,
                "window": 60
            },
            "low_frequency": {
                "limit": 10,
                "window": 60
            }
        }
    
    async def check_rate_limit(
        self,
        key: str,
        tier: str = "default"
    ) -> Dict[str, Any]:
        """Check if rate limit is exceeded for a key."""
        try:
            # Get rate limit config for tier
            config = self.rate_limits.get(tier, self.rate_limits["default"])
            
            # Generate Redis key
            redis_key = f"ratelimit:{key}:{int(time.time() // config['window'])}"
            
            # Get current count
            count = await redis_service.get_cache(redis_key)
            current_count = int(count) if count else 0
            
            # Check if limit exceeded
            if current_count >= config["limit"]:
                metrics.track_rate_limit_hit(key)
                return {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": config["limit"],
                    "window": config["window"],
                    "reset_time": (
                        (int(time.time() // config["window"]) + 1) * config["window"]
                    )
                }
            
            # Increment counter
            await redis_service.set_cache(
                redis_key,
                current_count + 1,
                expire_seconds=config["window"]
            )
            
            return {
                "allowed": True,
                "current_count": current_count + 1,
                "limit": config["limit"],
                "window": config["window"],
                "reset_time": (
                    (int(time.time() // config["window"]) + 1) * config["window"]
                )
            }
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # Default to allowing request in case of error
            return {
                "allowed": True,
                "error": str(e)
            }
    
    def get_tier_limits(self, tier: str) -> Dict[str, int]:
        """Get rate limit configuration for a tier."""
        return self.rate_limits.get(tier, self.rate_limits["default"])
    
    async def reset_limits(self, key: str):
        """Reset rate limits for a key."""
        try:
            pattern = f"ratelimit:{key}:*"
            keys = await redis_service.keys(pattern)
            for k in keys:
                await redis_service.delete(k)
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {str(e)}")

# Create global rate limiter instance
rate_limiter = RateLimiter() 