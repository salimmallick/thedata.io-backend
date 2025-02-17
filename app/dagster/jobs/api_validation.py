from dagster import job, op, Out, Nothing, DagsterType, In, RetryPolicy, Backoff
from typing import Dict, Any
import logging
from ...api.core.validation.api_validation import APIValidator
from ...api.core.monitoring.metrics import metrics
from ...api.core.storage.redis import redis
from contextlib import asynccontextmanager
import asyncio

logger = logging.getLogger(__name__)

# Initialize validator
api_validator = APIValidator()

# Define retry policy for validation operations
validation_retry_policy = RetryPolicy(
    max_retries=3,
    delay=30,
    backoff=Backoff.EXPONENTIAL
)

@asynccontextmanager
async def validation_context():
    """Context manager for validation operations"""
    try:
        # Ensure Redis connection
        if not redis._connected:
            await redis.connect()
        yield
    except Exception as e:
        logger.error(f"Validation context error: {str(e)}")
        raise
    finally:
        # Don't disconnect Redis as it might be used by other operations
        pass

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "rate_limiting"}
)
async def validate_rate_limiting(context) -> Dict[str, Any]:
    """Validate rate limiting functionality"""
    context.log.info("Validating rate limiting")
    
    try:
        async with validation_context():
            results = await api_validator.validate_rate_limiting()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Rate limiting issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Rate limiting recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Rate limiting validation failed: {str(e)}")
        metrics.track_validation_errors("rate_limiting")
        raise

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "authentication"}
)
async def validate_authentication(context) -> Dict[str, Any]:
    """Validate authentication and authorization"""
    context.log.info("Validating authentication")
    
    try:
        async with validation_context():
            results = await api_validator.validate_authentication()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Authentication issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Authentication recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Authentication validation failed: {str(e)}")
        metrics.track_validation_errors("authentication")
        raise

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "request_validation"}
)
async def validate_request_validation(context) -> Dict[str, Any]:
    """Validate request validation"""
    context.log.info("Validating request validation")
    
    try:
        async with validation_context():
            results = await api_validator.validate_request_validation()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Request validation issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Request validation recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Request validation failed: {str(e)}")
        metrics.track_validation_errors("request_validation")
        raise

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "error_handling"}
)
async def validate_error_handling(context) -> Dict[str, Any]:
    """Validate error handling"""
    context.log.info("Validating error handling")
    
    try:
        async with validation_context():
            results = await api_validator.validate_error_handling()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Error handling issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Error handling recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Error handling validation failed: {str(e)}")
        metrics.track_validation_errors("error_handling")
        raise

@op(
    ins={
        "rate_limiting": In(Dict[str, Any]),
        "authentication": In(Dict[str, Any]),
        "request_validation": In(Dict[str, Any]),
        "error_handling": In(Dict[str, Any])
    },
    tags={"validation": "evaluation"}
)
def evaluate_api_validation_results(
    context,
    rate_limiting: Dict[str, Any],
    authentication: Dict[str, Any],
    request_validation: Dict[str, Any],
    error_handling: Dict[str, Any]
) -> Nothing:
    """Evaluate all validation results and take necessary actions"""
    try:
        # Track overall validation status
        validation_status = "healthy"
        issues = []
        
        # Check rate limiting
        if rate_limiting.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(rate_limiting.get("issues", []))
        
        # Check authentication
        if authentication.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(authentication.get("issues", []))
        
        # Check request validation
        if request_validation.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(request_validation.get("issues", []))
        
        # Check error handling
        if error_handling.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(error_handling.get("issues", []))
        
        # Log overall status
        context.log.info(f"API validation status: {validation_status}")
        if issues:
            context.log.warning("Validation issues found:")
            for issue in issues:
                context.log.warning(f"- {issue}")
        
        # Track metrics
        metrics.track_api_validation_status(validation_status, len(issues))
        
        # Track component-specific metrics
        for component, result in {
            "rate_limiting": rate_limiting,
            "authentication": authentication,
            "request_validation": request_validation,
            "error_handling": error_handling
        }.items():
            metrics.track_api_component_health(
                component=component,
                status=result.get("status", "unknown")
            )
        
    except Exception as e:
        context.log.error(f"Error evaluating validation results: {str(e)}")
        metrics.track_validation_errors("evaluation")
        raise

@op(out={"internal_api_status": Out(Dict[str, Any])})
def validate_internal_apis():
    """Validate internal API endpoints."""
    # TODO: Implement internal API validation
    return {"status": "not_implemented", "message": "Internal API validation not implemented"}

@op(out={"external_api_status": Out(Dict[str, Any])})
def validate_external_apis():
    """Validate external API dependencies."""
    # TODO: Implement external API validation
    return {"status": "not_implemented", "message": "External API validation not implemented"}

@op(out={"auth_status": Out(Dict[str, Any])})
def validate_auth_service():
    """Validate authentication service."""
    # TODO: Implement auth service validation
    return {"status": "not_implemented", "message": "Auth service validation not implemented"}

@job(
    description="Comprehensive API validation job",
    tags={"category": "maintenance"}
)
def validate_api():
    """Job to validate all API endpoints and dependencies."""
    internal_result = validate_internal_apis()
    external_result = validate_external_apis()
    auth_result = validate_auth_service()
    
    rate_limiting_results = validate_rate_limiting()
    authentication_results = validate_authentication()
    request_validation_results = validate_request_validation()
    error_handling_results = validate_error_handling()
    
    evaluate_api_validation_results(
        rate_limiting_results,
        authentication_results,
        request_validation_results,
        error_handling_results
    ) 