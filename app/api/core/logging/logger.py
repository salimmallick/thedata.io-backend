"""
Centralized logging module with structured logging and context tracking.
"""
import logging
import sys
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import structlog
from pythonjsonlogger import jsonlogger
from ..monitoring.instances import metrics

# Context variables for request tracking
request_id: ContextVar[str] = ContextVar('request_id', default='')
user_id: ContextVar[str] = ContextVar('user_id', default='')
organization_id: ContextVar[str] = ContextVar('organization_id', default='')

class StructuredLogger:
    """Structured logger with context tracking and metrics integration."""
    
    def __init__(self):
        """Initialize structured logger."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure JSON logging
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(
            jsonlogger.JsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s'
            )
        )
        
        # Configure root logger
        root_logger = logging.getLogger()
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        root_logger.addHandler(json_handler)
        root_logger.setLevel(log_level)
        
        # Create structured logger
        self.logger = structlog.get_logger()
    
    def set_context(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Set context variables for logging."""
        if request_id:
            request_id.set(request_id)
        if user_id:
            user_id.set(user_id)
        if org_id:
            organization_id.set(org_id)
        
        # Add additional context
        for key, value in kwargs.items():
            self.logger = self.logger.bind(**{key: value})
    
    def clear_context(self) -> None:
        """Clear all context variables."""
        request_id.set('')
        user_id.set('')
        organization_id.set('')
        self.logger = structlog.get_logger()
    
    def _log(
        self,
        level: str,
        event: str,
        error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        """Internal logging method."""
        # Prepare log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id.get(),
            "user_id": user_id.get(),
            "organization_id": organization_id.get(),
            **kwargs
        }
        
        # Add error information if present
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": getattr(error, "__traceback__", None)
            })
            
            # Track error in metrics
            metrics.track_error(type(error).__name__, str(error))
        
        # Log with appropriate level
        log_method = getattr(self.logger, level)
        log_method(event, **log_data)
    
    def debug(self, event: str, **kwargs) -> None:
        """Log debug message."""
        self._log("debug", event, **kwargs)
    
    def info(self, event: str, **kwargs) -> None:
        """Log info message."""
        self._log("info", event, **kwargs)
    
    def warning(self, event: str, **kwargs) -> None:
        """Log warning message."""
        self._log("warning", event, **kwargs)
    
    def error(self, event: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        self._log("error", event, error=error, **kwargs)
    
    def critical(self, event: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message."""
        self._log("critical", event, error=error, **kwargs)
    
    def audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str,
        **kwargs
    ) -> None:
        """Log audit event."""
        self._log(
            "info",
            "audit_event",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            **kwargs
        )
    
    def metric(self, metric_name: str, value: float, **kwargs) -> None:
        """Log metric event."""
        self._log(
            "info",
            "metric_event",
            metric_name=metric_name,
            value=value,
            **kwargs
        )
        
        # Track metric
        metrics.track_custom_metric(metric_name, value)

# Create global logger instance
logger = StructuredLogger()

__all__ = ['logger', 'StructuredLogger'] 