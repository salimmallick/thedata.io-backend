"""
Main application module.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
import os

from app.api.core.config.settings import settings
from app.api.core.database import db_pool, init_db_pool
from app.api.core.middleware.tracing import TracingMiddleware
from app.api.core.tracing.tracer import TracingManager
from app.api.core.logging.config import configure_logging, get_logger
from app.api.core.monitoring import health_checker, metrics, init_monitoring
from app.api.core.errors.error_handler import (
    error_handler,
    BaseError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    DatabaseError,
    ServiceError,
    RateLimitError
)
from .core.middleware.logging import LoggingMiddleware
from .core.recovery.procedures import register_common_procedures
from .core.monitoring.service import monitoring_service
from .routers import (
    analytics, auth, data_sources, health,
    ingestion, organizations, pipelines,
    transform, users, admin
)
from app.api.core.recovery import recovery_manager, init_recovery_manager
from app.api.core.middleware import setup_middleware

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize tracing
tracing_manager = TracingManager()

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Initialize tracing
if settings.TRACING_ENABLED:
    try:
        tracing_manager.init_tracing(app)
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {str(e)}")
        # Continue without tracing

# Add middleware
setup_middleware(app)

@app.on_event("startup")
async def startup_event():
    """Initialize application resources on startup."""
    try:
        logger.info("Starting application", extra={
            "environment": settings.ENVIRONMENT,
            "version": settings.VERSION
        })
        
        # Initialize recovery manager first
        init_recovery_manager()
        logger.info("Recovery manager initialized")
        
        # Register recovery procedures before database initialization
        await register_common_procedures()
        logger.info("Registered common recovery procedures")
        
        # Initialize database pool with recovery manager
        await db_pool.init_pools()
        logger.info("Database pools initialized")
        
        # Set recovery manager in database pool
        db_pool.set_recovery_manager(recovery_manager)
        logger.info("Database pool recovery manager set")
        
        # Initialize monitoring and health checker
        await init_monitoring(db_pool=db_pool)
        logger.info("Monitoring initialized")
        
        # Start monitoring service
        await monitoring_service.start()
        logger.info("Monitoring service started")
        
        # Initialize tracing if enabled
        if settings.TRACING_ENABLED:
            tracing_manager.init_tracing(app)
            logger.info("Tracing initialized")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application resources on shutdown."""
    try:
        # Stop monitoring service
        await monitoring_service.stop()
        
        # Close database pools
        await db_pool.cleanup()
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Failed to shutdown application: {str(e)}")
        raise

@app.exception_handler(BaseError)
async def base_error_handler(request: Request, error: BaseError):
    """Handle all custom application errors."""
    return JSONResponse(
        status_code=error.status_code,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, error: ValidationError):
    """Handle validation errors."""
    logger.warning("Validation error", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, error: AuthenticationError):
    """Handle authentication errors."""
    logger.warning("Authentication error", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, error: AuthorizationError):
    """Handle authorization errors."""
    logger.warning("Authorization error", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(request: Request, error: ResourceNotFoundError):
    """Handle resource not found errors."""
    logger.warning("Resource not found", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, error: DatabaseError):
    """Handle database errors."""
    logger.error("Database error", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, error: ServiceError):
    """Handle service errors."""
    logger.error("Service error", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, error: RateLimitError):
    """Handle rate limit errors."""
    logger.warning("Rate limit exceeded", error=str(error), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_handler.handle_error(error)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, error: Exception):
    """Handle any unhandled exceptions."""
    logger.error(
        "Unhandled error",
        extra={
            "error": str(error),
            "path": request.url.path,
            "exc_info": True
        }
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_handler.handle_error(error)
    )

# Include routers with proper prefixes and tags
app.include_router(
    health.router,
    prefix=f"{settings.API_V1_STR}/health",
    tags=["Health"]
)
app.include_router(
    auth.router,
    prefix=settings.API_V1_STR,
    tags=["Authentication"]
)
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["Users"]
)
app.include_router(
    organizations.router,
    prefix=f"{settings.API_V1_STR}/organizations",
    tags=["Organizations"]
)
app.include_router(
    data_sources.router,
    prefix=f"{settings.API_V1_STR}/data-sources",
    tags=["Data Sources"]
)
app.include_router(
    pipelines.router,
    prefix=f"{settings.API_V1_STR}/pipelines",
    tags=["Pipelines"]
)
app.include_router(
    ingestion.router,
    prefix=f"{settings.API_V1_STR}/ingestion",
    tags=["Data Ingestion"]
)
app.include_router(
    transform.router,
    prefix=f"{settings.API_V1_STR}/transform",
    tags=["Transformation Rules"]
)
app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_STR}/analytics",
    tags=["Analytics"]
)
app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["Administration"]
)

# Remove duplicate health check endpoint since it's now handled by the health router
@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    try:
        # Initialize health checker if not already initialized
        if health_checker is None:
            init_monitoring(db_pool=db_pool)
            
        # Check health of all components
        health_status = await health_checker.check_all(db_pool)
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "unhealthy", "error": str(e)}
        )

__all__ = ['app'] 