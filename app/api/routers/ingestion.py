from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict, Any
from datetime import datetime
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..services.pipeline import pipeline_service
from ..models.timeseries import (
    TimeseriesData,
    MetricData,
    EventData,
    DataType,
    DataSource
)
import logging
import asyncio
from ..core.auth.rate_limit import RateLimiter
from ..core.data.transform import transformation_pipeline
from ..core.data.transform_config import config_manager
from ..core.monitoring.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])

# Permission checkers
require_ingest = PermissionChecker(["ingest_data"])

# Rate limiters
event_limiter = RateLimiter()
metric_limiter = RateLimiter()

@router.on_event("startup")
async def startup_event():
    """Initialize transformation rules on startup"""
    try:
        # Load and apply transformation configurations
        config_manager.apply_configs()
        logger.info("Transformation rules initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing transformation rules: {str(e)}")
        raise

async def process_event_batch(events: List[Dict[str, Any]]):
    """Process a batch of events"""
    try:
        # Apply transformation rules in batch
        transformed_events = await transformation_pipeline.process_batch(events)
        
        # Filter out None results (events that were filtered by rules)
        valid_events = [
            event for event in transformed_events
            if event is not None
        ]
        
        if valid_events:
            # Process the transformed events
            await pipeline_service._processors["events"].process_batch(valid_events)
            
        # Log statistics
        filtered_count = len(events) - len(valid_events)
        if filtered_count > 0:
            logger.info(f"{filtered_count} events filtered out by transformation rules")
            
    except Exception as e:
        logger.error(f"Error processing event batch: {str(e)}")
        raise

@router.post("/events")
async def ingest_event(
    event: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Ingest a single event"""
    background_tasks.add_task(process_event_batch, [event])
    return {"status": "accepted"}

@router.post("/events/batch")
async def ingest_events(
    events: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    batch_size: int = 100
):
    """Ingest multiple events with batching"""
    # Process events in batches
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        background_tasks.add_task(process_event_batch, batch)
    
    return {
        "status": "accepted",
        "count": len(events),
        "batches": (len(events) + batch_size - 1) // batch_size
    }

@router.post("/metrics")
async def ingest_metrics(
    metrics_data: List[MetricData],
    background_tasks: BackgroundTasks,
    request: Request,
    token = Depends(require_ingest)
):
    """Ingest metric data with rate limiting"""
    # Check rate limit
    org_id = token.org_id
    result = await metric_limiter.check_rate_limit(f"metrics:{org_id}", "high_frequency")
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for metric ingestion"
        )
    
    # Validate metrics
    for metric in metrics_data:
        if not metric.timestamp:
            metric.timestamp = datetime.utcnow()
    
    # Process metrics in background
    background_tasks.add_task(
        pipeline_service._processors["metrics"].process_batch,
        metrics_data
    )
    
    return {
        "status": "accepted",
        "count": len(metrics_data),
        "timestamp": datetime.utcnow()
    }

@router.post("/logs")
async def ingest_logs(
    logs: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    request: Request,
    token = Depends(require_ingest),
    batch_size: int = 100
):
    """Ingest log data with rate limiting and batching"""
    # Check rate limit
    org_id = token.org_id
    result = await event_limiter.check_rate_limit(f"logs:{org_id}", "high_frequency")
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for log ingestion"
        )
    
    # Process logs in batches
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i + batch_size]
        background_tasks.add_task(
            pipeline_service._processors["log_events"].process_batch,
            batch
        )
    
    return {
        "status": "accepted",
        "count": len(logs),
        "batches": (len(logs) + batch_size - 1) // batch_size,
        "timestamp": datetime.utcnow()
    }

@router.post("/traces")
async def ingest_traces(
    traces: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    request: Request,
    token = Depends(require_ingest),
    batch_size: int = 50  # Smaller batch size for traces
):
    """Ingest distributed trace data with rate limiting and batching"""
    # Check rate limit
    org_id = token.org_id
    result = await event_limiter.check_rate_limit(f"traces:{org_id}", "high_frequency")
    if not result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for trace ingestion"
        )
    
    # Process traces in batches
    for i in range(0, len(traces), batch_size):
        batch = traces[i:i + batch_size]
        background_tasks.add_task(
            pipeline_service._processors["log_events"].process_batch,
            batch,
            data_type="trace"
        )
    
    return {
        "status": "accepted",
        "count": len(traces),
        "batches": (len(traces) + batch_size - 1) // batch_size,
        "timestamp": datetime.utcnow()
    } 