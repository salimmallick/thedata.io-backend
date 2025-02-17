from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.utils.middleware import (
    SecurityHeadersMiddleware,
    AuditLogMiddleware,
    RateLimitMiddleware,
    CacheMiddleware,
    MonitoringMiddleware
)
from .core.storage.redis import redis
from .core.monitoring.metrics import metrics
from .routers import auth, users, organizations
from .core.config import settings
import logging
from prometheus_client import make_asgi_app
from .core.monitoring.health import health_checker
import asyncio
from .core.monitoring.tracing import tracing
from .core.storage.database_pool import db_pool
from .core.storage.query_optimizer import query_optimizer
from .core.utils.error_handling import error_handler, DataIngestionError, RateLimitExceededError
from fastapi import status
from .core.storage.database import init_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info("Starting theData.io API")
    try:
        # Initialize database pools
        await db_pool.init_pools()
        logger.info("Database pools initialized")
        
        # Track system info metrics
        metrics.track_component_health("api", True)
        
        # Connect to Redis
        await redis.connect()
        logger.info("Connected to Redis")
        
        # Initialize error handler
        await error_handler.initialize()
        logger.info("Initialized error handling system")
        
        await init_db()
        
        yield
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down theData.io API")
        try:
            # Clean up database pools
            await db_pool.cleanup()
            logger.info("Database pools cleaned up")
            
            # Clean up tracing
            tracing.cleanup()
            logger.info("Cleaned up tracing")
            
            # Reset query optimizer stats
            query_optimizer.reset_stats()
            
            # Disconnect from Redis
            await redis.disconnect()
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error(f"Shutdown error: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title="theData.io API",
    description="Backend API for theData.io platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Data Ingestion",
            "description": "Endpoints for ingesting events, metrics, and logs"
        },
        {
            "name": "Analytics",
            "description": "Endpoints for querying and analyzing data"
        }
    ]
)

# Initialize tracing
tracing.init_tracing(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security and performance middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CacheMiddleware)
app.add_middleware(MonitoringMiddleware)

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router)
app.include_router(organizations.router)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return await error_handler.handle_exception(request, exc)

@app.exception_handler(DataIngestionError)
async def ingestion_exception_handler(request: Request, exc: DataIngestionError):
    """Handle data ingestion errors"""
    return await error_handler.handle_exception(request, exc)

@app.exception_handler(RateLimitExceededError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError):
    """Handle rate limit errors"""
    return await error_handler.handle_exception(request, exc)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    pool_health = await db_pool.check_pool_health()
    return {
        "status": "healthy" if pool_health["status"] == "healthy" else "unhealthy",
        "database": pool_health
    } 