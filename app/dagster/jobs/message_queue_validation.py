from dagster import job, op, Out, Nothing, DagsterType, In, RetryPolicy, Backoff
from typing import Dict, Any
import logging
from ...api.core.validation.message_queue_validation import MessageQueueValidator
from ...api.core.monitoring.metrics import metrics
from ...api.core.storage.nats import nats_client
from contextlib import asynccontextmanager
import asyncio

logger = logging.getLogger(__name__)

# Initialize validator
message_queue_validator = MessageQueueValidator()

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
        # Ensure NATS connection
        if not nats_client.is_connected():
            await nats_client.connect()
        yield
    except Exception as e:
        logger.error(f"Validation context error: {str(e)}")
        raise
    finally:
        # Don't disconnect NATS as it might be used by other operations
        pass

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "streams"}
)
async def validate_streams(context) -> Dict[str, Any]:
    """Validate NATS streams"""
    context.log.info("Validating NATS streams")
    
    try:
        async with validation_context():
            results = await message_queue_validator.validate_streams()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Stream issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Stream recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Stream validation failed: {str(e)}")
        metrics.track_validation_errors("streams")
        raise

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "consumers"}
)
async def validate_consumers(context) -> Dict[str, Any]:
    """Validate consumer groups"""
    context.log.info("Validating consumer groups")
    
    try:
        async with validation_context():
            results = await message_queue_validator.validate_consumers()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Consumer issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Consumer recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Consumer validation failed: {str(e)}")
        metrics.track_validation_errors("consumers")
        raise

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "message_delivery"}
)
async def validate_message_delivery(context) -> Dict[str, Any]:
    """Validate message delivery"""
    context.log.info("Validating message delivery")
    
    try:
        async with validation_context():
            results = await message_queue_validator.validate_message_delivery()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Message delivery issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Message delivery recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Message delivery validation failed: {str(e)}")
        metrics.track_validation_errors("message_delivery")
        raise

@op(
    out=Out(Dict[str, Any]),
    retry_policy=validation_retry_policy,
    tags={"validation": "backpressure"}
)
async def validate_backpressure(context) -> Dict[str, Any]:
    """Validate backpressure handling"""
    context.log.info("Validating backpressure handling")
    
    try:
        async with validation_context():
            results = await message_queue_validator.validate_backpressure()
            
            # Log any issues found
            for issue in results.get("issues", []):
                context.log.warning(f"Backpressure issue: {issue}")
            for recommendation in results.get("recommendations", []):
                context.log.info(f"Backpressure recommendation: {recommendation}")
            
            return results
    except Exception as e:
        context.log.error(f"Backpressure validation failed: {str(e)}")
        metrics.track_validation_errors("backpressure")
        raise

@op(
    ins={
        "streams": In(Dict[str, Any]),
        "consumers": In(Dict[str, Any]),
        "message_delivery": In(Dict[str, Any]),
        "backpressure": In(Dict[str, Any])
    },
    tags={"validation": "evaluation"}
)
def evaluate_message_queue_validation_results(
    context,
    streams: Dict[str, Any],
    consumers: Dict[str, Any],
    message_delivery: Dict[str, Any],
    backpressure: Dict[str, Any]
) -> Nothing:
    """Evaluate all validation results and take necessary actions"""
    try:
        # Track overall validation status
        validation_status = "healthy"
        issues = []
        
        # Check streams
        if streams.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(streams.get("issues", []))
        
        # Check consumers
        if consumers.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(consumers.get("issues", []))
        
        # Check message delivery
        if message_delivery.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(message_delivery.get("issues", []))
        
        # Check backpressure
        if backpressure.get("status") != "healthy":
            validation_status = "degraded"
            issues.extend(backpressure.get("issues", []))
        
        # Log overall status
        context.log.info(f"Message queue validation status: {validation_status}")
        if issues:
            context.log.warning("Validation issues found:")
            for issue in issues:
                context.log.warning(f"- {issue}")
        
        # Track metrics
        metrics.track_mq_validation_status(validation_status, len(issues))
        
        # Track component-specific metrics
        for component, result in {
            "streams": streams,
            "consumers": consumers,
            "message_delivery": message_delivery,
            "backpressure": backpressure
        }.items():
            metrics.track_mq_component_health(
                component=component,
                status=result.get("status", "unknown")
            )
        
    except Exception as e:
        context.log.error(f"Error evaluating validation results: {str(e)}")
        metrics.track_validation_errors("evaluation")
        raise

@op(out={"nats_status": Out(Dict[str, Any])})
def validate_nats():
    """Validate NATS message queue connectivity and health."""
    # TODO: Implement NATS validation
    return {"status": "not_implemented", "message": "NATS validation not implemented"}

@op(out={"kafka_status": Out(Dict[str, Any])})
def validate_kafka():
    """Validate Kafka message queue connectivity and health."""
    # TODO: Implement Kafka validation
    return {"status": "not_implemented", "message": "Kafka validation not implemented"}

@op(out={"rabbitmq_status": Out(Dict[str, Any])})
def validate_rabbitmq():
    """Validate RabbitMQ connectivity and health."""
    # TODO: Implement RabbitMQ validation
    return {"status": "not_implemented", "message": "RabbitMQ validation not implemented"}

@job(
    description="Comprehensive message queue validation job",
    tags={"category": "maintenance"}
)
def validate_message_queue():
    """Job to validate all message queue connections and health."""
    nats_result = validate_nats()
    kafka_result = validate_kafka()
    rabbitmq_result = validate_rabbitmq()
    
    streams_results = validate_streams()
    consumers_results = validate_consumers()
    message_delivery_results = validate_message_delivery()
    backpressure_results = validate_backpressure()
    
    evaluate_message_queue_validation_results(
        streams_results,
        consumers_results,
        message_delivery_results,
        backpressure_results
    ) 