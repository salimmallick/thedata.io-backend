"""
Base router with integrated error recovery for critical operations.
"""
from fastapi import APIRouter, Request, Response
from typing import Callable, Any, Optional
import functools
import uuid
from ..logging.logger import logger
from ..recovery.manager import recovery_manager

class RecoverableRouter(APIRouter):
    """Router with integrated error recovery for critical operations."""
    
    def recoverable(
        self,
        operation_id: str,
        *,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """
        Decorator to mark an endpoint as recoverable.
        
        Args:
            operation_id: Unique identifier for the operation
            include_in_schema: Whether to include the endpoint in OpenAPI schema
            **kwargs: Additional arguments to pass to the recovery manager
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract request from args or kwargs
                request = next(
                    (arg for arg in args if isinstance(arg, Request)),
                    kwargs.get("request")
                )
                
                if not request:
                    return await func(*args, **kwargs)
                
                # Generate unique transaction ID
                transaction_id = str(uuid.uuid4())
                
                try:
                    # Execute the operation
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(
                        f"Operation {operation_id} failed",
                        extra={
                            "operation_id": operation_id,
                            "transaction_id": transaction_id,
                            "error": str(e)
                        }
                    )
                    
                    # Attempt recovery
                    try:
                        await recovery_manager.execute_recovery(
                            operation_id,
                            context={
                                "transaction_id": transaction_id,
                                "request": {
                                    "method": request.method,
                                    "url": str(request.url),
                                    "headers": dict(request.headers),
                                    "query_params": dict(request.query_params),
                                    "path_params": dict(request.path_params)
                                },
                                "error": str(e)
                            }
                        )
                        
                        # Retry the operation after recovery
                        return await func(*args, **kwargs)
                        
                    except Exception as recovery_error:
                        logger.error(
                            f"Recovery failed for operation {operation_id}",
                            extra={
                                "operation_id": operation_id,
                                "transaction_id": transaction_id,
                                "error": str(recovery_error)
                            }
                        )
                        raise
            
            # Register the endpoint with FastAPI
            return super(RecoverableRouter, self).api_route(
                path=kwargs.pop("path", "/"),
                include_in_schema=include_in_schema,
                **kwargs
            )(wrapper)
        
        return decorator

__all__ = ['RecoverableRouter'] 