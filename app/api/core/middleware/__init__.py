"""Middleware initialization module."""
from fastapi import FastAPI
from .logging import LoggingMiddleware
from .tracing import TracingMiddleware

def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application."""
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TracingMiddleware) 