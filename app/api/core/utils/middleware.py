from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Awaitable
import time
from ..auth.security import security
from ..storage.redis import redis
from ..monitoring.metrics import metrics
from ..storage.cache import cache_manager
from starlette.responses import StreamingResponse, Response
import json
from ..config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdn.redoc.ly; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data: fastapi.tiangolo.com; connect-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        # Only add HSTS in production
        if settings.ENVIRONMENT == "production":
            self.security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Start timer for request duration
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # Add request ID for tracing
        request_id = request.headers.get("X-Request-ID") or str(time.time())
        response.headers["X-Request-ID"] = request_id
        
        # Add response time header
        duration = time.time() - start_time
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response

class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses for audit"""
    
    async def get_response_body(self, response: Response) -> str:
        if isinstance(response, StreamingResponse):
            # For streaming responses, we don't capture the body
            return "<streaming response>"
        elif hasattr(response, "body"):
            try:
                return response.body.decode()
            except:
                return "<binary response>"
        return "<no response body>"
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Process request
        response = await call_next(request)
        
        # Get organization if available
        org = getattr(request.state, "organization", None)
        
        if org:
            # Log request/response for audit
            try:
                response_body = await self.get_response_body(response)
                
                await security.audit_log_request(
                    request=request,
                    org=org,
                    response_status=response.status_code,
                    response_body=response_body
                )
            except Exception as e:
                # Log error but don't block response
                print(f"Error in audit logging: {str(e)}")
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to requests using Redis"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.tier_limits = {
            "free": 1000,      # 1000 requests per minute
            "basic": 5000,     # 5000 requests per minute
            "premium": 20000   # 20000 requests per minute
        }
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Get organization if available
        org = getattr(request.state, "organization", None)
        
        if org:
            # Get rate limit for organization tier
            limit = self.tier_limits.get(org.tier, 1000)
            window = 60  # 1 minute window
            
            # Check rate limit in Redis
            if not await redis.check_rate_limit(
                key=f"org:{org.id}",
                limit=limit,
                window=window
            ):
                # Get rate limit info for headers
                info = await redis.get_rate_limit_info(
                    key=f"org:{org.id}",
                    window=window
                )
                
                return Response(
                    content="Rate limit exceeded",
                    status_code=429,
                    headers={
                        "Retry-After": str(info["ttl"]),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(max(0, limit - info["count"])),
                        "X-RateLimit-Reset": str(info["ttl"])
                    }
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            info = await redis.get_rate_limit_info(
                key=f"org:{org.id}",
                window=window
            )
            
            response.headers.update({
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - info["count"])),
                "X-RateLimit-Reset": str(info["ttl"])
            })
            
            return response
        
        return await call_next(request)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Collect metrics for monitoring"""
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Track request metrics
            metrics.track_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=process_time
            )
            
            # Track organization-specific metrics if available
            org = getattr(request.state, "organization", None)
            if org:
                # Track rate limit metrics if rate limited
                if response.status_code == 429:
                    metrics.track_rate_limit_hit(org.tier)
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            # Track error metrics
            metrics.track_error(
                error_type=type(e).__name__
            )
            raise

class CacheMiddleware(BaseHTTPMiddleware):
    """Cache responses using advanced cache management"""
    
    async def get_response_data(self, response: Response) -> dict:
        if isinstance(response, StreamingResponse):
            # Don't cache streaming responses
            return None
            
        try:
            if hasattr(response, "body"):
                return {
                    "content": response.body.decode(),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type
                }
        except:
            pass
        return None
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Generate cache key from request
        cache_key = f"cache:{request.method}:{request.url.path}:{request.query_params}"
        
        # Try to get from cache
        cached_response = await cache_manager.get(cache_key)
        if cached_response:
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"],
                media_type=cached_response["media_type"]
            )
        
        # Get fresh response
        response = await call_next(request)
        
        # Cache successful responses
        if 200 <= response.status_code < 400:
            # Define invalidation patterns based on URL path
            patterns = [
                f"cache:{request.method}:{request.url.path}:*",  # Same path, different params
                f"cache:*:{request.url.path}:*"  # Same path, any method
            ]
            
            response_data = await self.get_response_data(response)
            if response_data:
                await cache_manager.set(
                    key=cache_key,
                    value=response_data,
                    patterns=patterns
                )
        
        return response 