"""
FastAPI middleware for request tracing using OpenTelemetry.
"""
from typing import Callable
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.core.config.settings import settings
from app.api.core.tracing.tracer import TracingManager

class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracing HTTP requests using OpenTelemetry."""

    def __init__(self, app: ASGIApp):
        """Initialize the middleware.
        
        Args:
            app: The ASGI application.
        """
        super().__init__(app)
        self.tracer = TracingManager()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add tracing information.
        
        Args:
            request: The incoming request.
            call_next: The next middleware in the chain.
            
        Returns:
            The response from the next middleware.
        """
        if not settings.TRACING_ENABLED or request.url.path in settings.TRACE_EXCLUDED_URLS:
            return await call_next(request)

        with self.tracer.start_span(
            name=f"{request.method} {request.url.path}",
            context={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.target": request.url.path,
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.request_content_length": request.headers.get("content-length", 0),
                "http.flavor": request.scope.get("http_version", "1.1"),
                "net.peer.ip": request.client.host if request.client else "",
                "net.peer.port": request.client.port if request.client else 0,
            }
        ) as span:
            try:
                start_time = time.time()
                response = await call_next(request)
                duration = time.time() - start_time
                
                # Add response attributes
                self.tracer.add_span_attributes(span, {
                    "http.status_code": response.status_code,
                    "http.response_content_length": response.headers.get("content-length", 0),
                    "http.duration": duration,
                })
                
                return response
            except Exception as e:
                # Record the exception in the span
                self.tracer.record_exception(span, e)
                raise

__all__ = ['TracingMiddleware'] 