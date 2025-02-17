from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import logging
import yaml
import os
from .api.routers import (
    ingestion,
    analytics,
    transform,
    health
)
from .api.core.schema.init import schema_initializer
from .api.core.nats import nats_client

# Load logging configuration
with open("app/log_config.yml", "r") as f:
    log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)

logger = logging.getLogger(__name__)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="theData.io API",
        version="1.0.0",
        description="Event ingestion, metrics collection, and real-time analytics API",
        routes=app.routes,
        tags=[
            {"name": "Ingestion", "description": "Event and metric ingestion endpoints"},
            {"name": "Analytics", "description": "Real-time and historical analytics"},
            {"name": "Transformation", "description": "Data transformation rules"},
            {"name": "Health", "description": "Health and status checks"}
        ]
    )
    
    # Custom OpenAPI schema modifications
    openapi_schema["info"]["x-logo"] = {
        "url": "https://thedata.io/logo.png"
    }
    
    # Security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Initialize FastAPI app
app = FastAPI(
    title="theData.io API",
    description="Event ingestion, metrics collection, and real-time analytics API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Set custom OpenAPI schema
app.openapi = custom_openapi

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check model
class HealthCheck(BaseModel):
    status: str
    version: str
    timestamp: datetime

@app.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    """
    Health check endpoint to verify API status
    """
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )

@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": "theData.io Platform API",
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
    )

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    try:
        # Initialize database schemas
        await schema_initializer.initialize_all()
        
        # Connect to NATS
        await nats_client.connect()
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        # Disconnect from NATS
        await nats_client.disconnect()
        
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=log_config
    ) 