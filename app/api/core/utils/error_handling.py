from typing import Dict, Any, Optional, Type, List
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import traceback
import logging
from ..monitoring.metrics import metrics
from datetime import datetime, timedelta
import json
from .circuit_breaker import CircuitBreakerError
from ..storage.redis import redis
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import time

logger = logging.getLogger(__name__)

class BaseError(Exception):
    """Base error class for application errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class DataValidationError(BaseError):
    """Raised when data validation fails"""
    pass

class RateLimitExceededError(BaseError):
    """Raised when rate limit is exceeded"""
    pass

class DataIngestionError(BaseError):
    """Base class for data ingestion errors"""
    def __init__(self, message: str, source: str, data: Any):
        super().__init__(message, {"source": source, "data": data})
        self.source = source
        self.data = data

class DatabaseError(BaseError):
    """Raised for database-related errors"""
    def __init__(self, message: str, database: str, operation: str):
        super().__init__(message, {"database": database, "operation": operation})
        self.database = database
        self.operation = operation

class AuthenticationError(BaseError):
    """Raised for authentication-related errors"""
    pass

class AuthorizationError(BaseError):
    """Raised for authorization-related errors"""
    pass

class ConfigurationError(BaseError):
    """Raised for configuration-related errors"""
    pass

class ServiceUnavailableError(BaseError):
    """Raised when a required service is unavailable"""
    def __init__(self, message: str, service: str):
        super().__init__(message, {"service": service})
        self.service = service

class RetryableError(BaseError):
    """Base class for errors that can be retried"""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, {"retry_after": retry_after})
        self.retry_after = retry_after

class ErrorHandler:
    """Enhanced error handling for the application"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_windows: Dict[str, List[float]] = {}
        self.error_thresholds = {
            "validation": {"count": 100, "window": 60},    # 100 per minute
            "rate_limit": {"count": 50, "window": 60},     # 50 per minute
            "ingestion": {"count": 20, "window": 60},      # 20 per minute
            "database": {"count": 10, "window": 60},       # 10 per minute
            "authentication": {"count": 30, "window": 60},  # 30 per minute
            "authorization": {"count": 20, "window": 60}    # 20 per minute
        }
        
        # Retry configurations
        self.retry_configs = {
            DataIngestionError: {"attempts": 3, "delay": 1, "max_delay": 10},
            DatabaseError: {"attempts": 5, "delay": 2, "max_delay": 30},
            ServiceUnavailableError: {"attempts": 3, "delay": 5, "max_delay": 60}
        }
        
        # Initialize cleanup task as None
        self._cleanup_task = None
        self._running = False
    
    async def initialize(self):
        """Initialize the error handler with async tasks"""
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = loop.create_task(self._cleanup_error_windows())
                logger.info("Started error window cleanup task")
        return self
    
    async def shutdown(self):
        """Shutdown the error handler and cleanup tasks"""
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Error handler shutdown complete")
    
    async def handle_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Enhanced exception handling with retry support"""
        error_id = f"{datetime.utcnow().isoformat()}-{id(exc)}"
        
        # Track error metrics
        metrics.track_error(
            error_type=type(exc).__name__
        )
        
        try:
            if isinstance(exc, ValidationError):
                return await self._handle_validation_error(error_id, exc)
            elif isinstance(exc, RateLimitExceededError):
                return await self._handle_rate_limit_error(error_id, exc)
            elif isinstance(exc, DataIngestionError):
                return await self._handle_ingestion_error(error_id, exc)
            elif isinstance(exc, DatabaseError):
                return await self._handle_database_error(error_id, exc)
            elif isinstance(exc, AuthenticationError):
                return await self._handle_authentication_error(error_id, exc)
            elif isinstance(exc, AuthorizationError):
                return await self._handle_authorization_error(error_id, exc)
            elif isinstance(exc, CircuitBreakerError):
                return await self._handle_circuit_breaker_error(error_id, exc)
            elif isinstance(exc, RetryableError):
                return await self._handle_retryable_error(error_id, exc)
            else:
                return await self._handle_unknown_error(error_id, exc)
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error_id": error_id,
                    "type": "error_handler_failure",
                    "message": "Error handling system failure"
                }
            )
    
    async def _handle_validation_error(
        self,
        error_id: str,
        exc: ValidationError
    ) -> JSONResponse:
        """Handle data validation errors with detailed tracking"""
        logger.warning(f"Validation error {error_id}: {str(exc)}")
        
        # Track validation error with details
        self._track_error("validation", error_details={
            "error_type": "validation",
            "fields": [e["loc"] for e in exc.errors()]
        })
        
        return JSONResponse(
            status_code=422,
            content={
                "error_id": error_id,
                "type": "validation_error",
                "message": "Data validation failed",
                "details": {
                    "errors": exc.errors(),
                    "recommendations": self._generate_validation_recommendations(exc)
                }
            }
        )
    
    async def _handle_rate_limit_error(
        self,
        error_id: str,
        exc: RateLimitExceededError
    ) -> JSONResponse:
        """Handle rate limit errors with retry information"""
        logger.warning(f"Rate limit error {error_id}: {str(exc)}")
        
        # Track rate limit error
        self._track_error("rate_limit")
        
        # Get rate limit info
        rate_limit_info = await self._get_rate_limit_info(exc)
        
        return JSONResponse(
            status_code=429,
            content={
                "error_id": error_id,
                "type": "rate_limit_error",
                "message": str(exc),
                "details": rate_limit_info
            },
            headers={
                "Retry-After": str(rate_limit_info["retry_after"]),
                "X-RateLimit-Reset": str(rate_limit_info["reset_time"])
            }
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(DataIngestionError)
    )
    async def _handle_ingestion_error(
        self,
        error_id: str,
        exc: DataIngestionError
    ) -> JSONResponse:
        """Handle data ingestion errors with retry mechanism"""
        logger.error(
            f"Ingestion error {error_id} from {exc.source}: {exc.message}",
            extra={
                "error_id": error_id,
                "source": exc.source,
                "data": exc.data
            }
        )
        
        # Track ingestion error
        self._track_error("ingestion", error_details={
            "source": exc.source,
            "data_size": len(str(exc.data))
        })
        
        # Store failed data for retry
        retry_key = await self._store_failed_ingestion(error_id, exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "error_id": error_id,
                "type": "ingestion_error",
                "message": exc.message,
                "details": {
                    "retry_key": retry_key,
                    "retry_available": True,
                    "source": exc.source
                }
            }
        )
    
    async def _handle_database_error(
        self,
        error_id: str,
        exc: DatabaseError
    ) -> JSONResponse:
        """Handle database errors with circuit breaker integration"""
        logger.error(
            f"Database error {error_id}: {str(exc)}",
            extra={
                "database": exc.database,
                "operation": exc.operation
            }
        )
        
        # Track database error
        self._track_error("database", error_details={
            "database": exc.database,
            "operation": exc.operation
        })
        
        return JSONResponse(
            status_code=503,
            content={
                "error_id": error_id,
                "type": "database_error",
                "message": str(exc),
                "details": {
                    "database": exc.database,
                    "operation": exc.operation,
                    "retry_available": isinstance(exc, RetryableError)
                }
            }
        )
    
    async def _handle_authentication_error(
        self,
        error_id: str,
        exc: AuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors"""
        logger.warning(f"Authentication error {error_id}: {str(exc)}")
        
        # Track authentication error
        self._track_error("authentication")
        
        return JSONResponse(
            status_code=401,
            content={
                "error_id": error_id,
                "type": "authentication_error",
                "message": str(exc)
            }
        )
    
    async def _handle_authorization_error(
        self,
        error_id: str,
        exc: AuthorizationError
    ) -> JSONResponse:
        """Handle authorization errors"""
        logger.warning(f"Authorization error {error_id}: {str(exc)}")
        
        # Track authorization error
        self._track_error("authorization")
        
        return JSONResponse(
            status_code=403,
            content={
                "error_id": error_id,
                "type": "authorization_error",
                "message": str(exc)
            }
        )
    
    async def _handle_circuit_breaker_error(
        self,
        error_id: str,
        exc: CircuitBreakerError
    ) -> JSONResponse:
        """Handle circuit breaker errors"""
        logger.error(f"Circuit breaker error {error_id}: {str(exc)}")
        
        return JSONResponse(
            status_code=503,
            content={
                "error_id": error_id,
                "type": "circuit_breaker_error",
                "message": str(exc),
                "details": {
                    "retry_after": 60  # Default retry after 1 minute
                }
            },
            headers={"Retry-After": "60"}
        )
    
    async def _handle_retryable_error(
        self,
        error_id: str,
        exc: RetryableError
    ) -> JSONResponse:
        """Handle retryable errors"""
        logger.warning(f"Retryable error {error_id}: {str(exc)}")
        
        return JSONResponse(
            status_code=503,
            content={
                "error_id": error_id,
                "type": "retryable_error",
                "message": str(exc),
                "details": {
                    "retry_after": exc.retry_after
                }
            },
            headers={"Retry-After": str(exc.retry_after)}
        )
    
    async def _handle_unknown_error(
        self,
        error_id: str,
        exc: Exception
    ) -> JSONResponse:
        """Handle unknown errors"""
        logger.error(
            f"Unknown error {error_id}: {str(exc)}",
            extra={
                "error_id": error_id,
                "traceback": traceback.format_exc()
            }
        )
        
        # Track unknown error
        metrics.track_error("unknown")
        
        return JSONResponse(
            status_code=500,
            content={
                "error_id": error_id,
                "type": "internal_error",
                "message": "An internal error occurred",
                "details": {"error_id": error_id}
            }
        )
    
    def _track_error(
        self,
        error_type: str,
        error_details: Dict[str, Any] = None
    ):
        """Track error occurrence with window-based counting"""
        current_time = time.time()
        
        # Initialize window if needed
        if error_type not in self.error_windows:
            self.error_windows[error_type] = []
        
        # Add error timestamp to window
        self.error_windows[error_type].append(current_time)
        
        # Update error count
        window_start = current_time - self.error_thresholds[error_type]["window"]
        self.error_windows[error_type] = [
            ts for ts in self.error_windows[error_type]
            if ts > window_start
        ]
        
        count = len(self.error_windows[error_type])
        
        # Check if threshold is exceeded
        if count > self.error_thresholds[error_type]["count"]:
            logger.critical(
                f"Error threshold exceeded for {error_type}: {count} errors in "
                f"{self.error_thresholds[error_type]['window']} seconds"
            )
            metrics.track_threshold_exceeded(error_type)
    
    async def _cleanup_error_windows(self):
        """Periodic cleanup of error windows"""
        while self._running:
            try:
                current_time = time.time()
                async with asyncio.Lock():  # Add lock for thread safety
                    for error_type in list(self.error_windows.keys()):
                        window_start = current_time - self.error_thresholds[error_type]["window"]
                        self.error_windows[error_type] = [
                            ts for ts in self.error_windows[error_type]
                            if ts > window_start
                        ]
            except Exception as e:
                logger.error(f"Error window cleanup failed: {str(e)}")
            
            await asyncio.sleep(60)  # Cleanup every minute
    
    def _generate_validation_recommendations(
        self,
        exc: ValidationError
    ) -> List[str]:
        """Generate helpful recommendations for validation errors"""
        recommendations = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            if error["type"] == "value_error.missing":
                recommendations.append(f"Provide a value for required field: {field}")
            elif error["type"] == "type_error":
                recommendations.append(
                    f"Provide correct type for field {field}: {error['msg']}"
                )
            elif error["type"] == "value_error.datetime":
                recommendations.append(
                    f"Provide datetime in ISO format for field {field}"
                )
        return recommendations
    
    async def _get_rate_limit_info(
        self,
        exc: RateLimitExceededError
    ) -> Dict[str, Any]:
        """Get rate limit information"""
        try:
            info = await redis.get_rate_limit_info(
                exc.details.get("key", ""),
                exc.details.get("window", 60)
            )
            return {
                "current_usage": info["count"],
                "limit": exc.details.get("limit", 0),
                "retry_after": info["ttl"],
                "reset_time": int(time.time()) + info["ttl"]
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {str(e)}")
            return {
                "retry_after": 60,
                "reset_time": int(time.time()) + 60
            }
    
    async def _store_failed_ingestion(
        self,
        error_id: str,
        exc: DataIngestionError
    ) -> str:
        """Store failed ingestion data in Redis."""
        try:
            cache_key = f"failed_ingestion:{error_id}"
            cache_data = {
                "source": exc.source,
                "data": exc.data,
                "timestamp": datetime.utcnow().isoformat()
            }
            await redis.set_cache(cache_key, json.dumps(cache_data), ex=3600)  # 1 hour expiration
            return error_id
        except Exception as e:
            logger.error(f"Failed to store ingestion error: {str(e)}")
            return error_id

async def handle_error(request: Request, exc: Exception) -> JSONResponse:
    """Global error handler function"""
    error_handler = ErrorHandler()
    await error_handler.initialize()
    try:
        return await error_handler.handle_exception(request, exc)
    finally:
        await error_handler.shutdown()

# Create error handler instance without starting cleanup task
error_handler = ErrorHandler() 