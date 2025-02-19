"""
Logging configuration module.
"""
import logging
import logging.config
import json
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger
from ..config.settings import settings

def configure_logging() -> None:
    """Configure logging for the application."""
    
    # Configure standard logging
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': jsonlogger.JsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'json' if settings.LOG_FORMAT == 'json' else 'standard',
                'level': settings.LOG_LEVEL
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
                'level': settings.LOG_LEVEL
            }
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': settings.LOG_LEVEL
        },
        'loggers': {
            'uvicorn': {
                'handlers': ['console'],
                'level': settings.LOG_LEVEL,
                'propagate': False
            },
            'fastapi': {
                'handlers': ['console'],
                'level': settings.LOG_LEVEL,
                'propagate': False
            }
        }
    })
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_app_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True
    )

def _add_app_info(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add application info to log events."""
    event_dict.update({
        "app_name": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    })
    return event_dict

class RequestIdFilter(logging.Filter):
    """Filter to add request ID to log records."""
    
    def __init__(self, request_id: str = None):
        self.request_id = request_id
        super().__init__()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to log record."""
        record.request_id = self.request_id
        return True

class ServiceContextFilter(logging.Filter):
    """Filter to add service context to log records."""
    
    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
        super().__init__()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add service context to log record."""
        record.service_name = self.service_name
        record.version = self.version
        return True

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)

__all__ = ['configure_logging', 'get_logger', 'RequestIdFilter', 'ServiceContextFilter'] 