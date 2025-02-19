"""
Logging middleware module.
"""
import time
import uuid
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
org_id_var: ContextVar[str] = ContextVar('org_id', default='')

logger = structlog.get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and context tracking."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process the request and add logging context."""
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Extract user and org IDs from request if available
        user_id = request.headers.get('X-User-ID', '')
        org_id = request.headers.get('X-Organization-ID', '')
        user_id_var.set(user_id)
        org_id_var.set(org_id)
        
        # Start timing the request
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            org_id=org_id,
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log request completion
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                user_id=user_id,
                org_id=org_id
            )
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            return response
            
        except Exception as e:
            # Log error details
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=duration,
                user_id=user_id,
                org_id=org_id,
                exc_info=True
            )
            raise
        finally:
            # Clear context variables
            request_id_var.set('')
            user_id_var.set('')
            org_id_var.set('')

def get_request_id() -> str:
    """Get the current request ID."""
    return request_id_var.get()

def get_user_id() -> str:
    """Get the current user ID."""
    return user_id_var.get()

def get_org_id() -> str:
    """Get the current organization ID."""
    return org_id_var.get()

__all__ = [
    'LoggingMiddleware',
    'get_request_id',
    'get_user_id',
    'get_org_id'
] 