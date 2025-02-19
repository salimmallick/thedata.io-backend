"""
Centralized error handling module.
"""
from typing import Dict, Any, Optional, Type
from fastapi import HTTPException, status
from ..logging.logger import logger
from ..monitoring.instances import metrics

class BaseError(Exception):
    """Base error class for application errors."""
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

class ValidationError(BaseError):
    """Raised when request validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class AuthenticationError(BaseError):
    """Raised when authentication fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class AuthorizationError(BaseError):
    """Raised when authorization fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class ResourceNotFoundError(BaseError):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

class DatabaseError(BaseError):
    """Raised when a database operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class ServiceError(BaseError):
    """Raised when a service operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class RateLimitError(BaseError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )

class ErrorHandler:
    """Centralized error handler."""
    
    def __init__(self):
        self.error_mapping: Dict[Type[Exception], Type[BaseError]] = {
            ValueError: ValidationError,
            KeyError: ValidationError,
            PermissionError: AuthorizationError,
            FileNotFoundError: ResourceNotFoundError
        }
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle any error and return standardized response."""
        if isinstance(error, BaseError):
            return self._format_error_response(error)
        
        # Map standard Python exceptions to our custom errors
        error_class = self.error_mapping.get(type(error))
        if error_class:
            custom_error = error_class(str(error))
            return self._format_error_response(custom_error)
        
        # Handle unknown errors
        return self._handle_unknown_error(error)
    
    def _format_error_response(self, error: BaseError) -> Dict[str, Any]:
        """Format error response."""
        response = {
            "error": {
                "code": error.error_code,
                "message": error.message,
                "status_code": error.status_code
            }
        }
        
        if error.details:
            response["error"]["details"] = error.details
        
        # Log error
        logger.error(
            "Error occurred",
            error_code=error.error_code,
            error_message=error.message,
            status_code=error.status_code,
            details=error.details
        )
        
        # Track error metrics
        metrics.track_error(error.error_code, error.message)
        
        return response
    
    def _handle_unknown_error(self, error: Exception) -> Dict[str, Any]:
        """Handle unknown errors."""
        error_response = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        }
        
        # Log the full error details for debugging
        logger.error(
            "Unknown error occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=True
        )
        
        # Track unknown error metric
        metrics.track_error("unknown_error", str(error))
        
        return error_response

# Global error handler instance
error_handler = ErrorHandler()

__all__ = [
    'BaseError',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'ResourceNotFoundError',
    'DatabaseError',
    'ServiceError',
    'RateLimitError',
    'error_handler'
] 