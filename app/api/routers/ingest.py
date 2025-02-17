from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any
from ..core.security import get_current_user_token, PermissionChecker
from ..core.database import get_nats_client, get_questdb_sender
from ..services.materialize import materialize_service
from ..models.timeseries import (
    TimeseriesData,
    MetricData,
    EventData,
    MaterializedView,
    MaterializedAggregation
)
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])

# Permission checkers
require_ingest = PermissionChecker(["ingest_data"])
require_view_management = PermissionChecker(["manage_views"])

@router.post("/metrics", status_code=status.HTTP_202_ACCEPTED)
async def ingest_metrics(
    metrics: List[MetricData],
    background_tasks: BackgroundTasks,
    token = Depends(require_ingest)
):
    """
    Ingest metrics data.
    Data will be:
    1. Published to NATS for real-time processing
    2. Stored in QuestDB for time-series storage
    3. Processed by Materialize for real-time analytics
    """
    async def process_metrics(metrics: List[MetricData]):
        try:
            # Get NATS client
            nc = await get_nats_client()
            
            # Publish to NATS for real-time processing
            for metric in metrics:
                await nc.publish(
                    "metrics.raw",
                    json.dumps(metric.dict()).encode()
                )
            
            # Store in QuestDB
            questdb = get_questdb_sender()
            with questdb as sender:
                for metric in metrics:
                    sender.row(
                        "metrics",
                        symbols={
                            'name': metric.name,
                            'source': metric.source,
                            'type': metric.type
                        },
                        columns={
                            'value': metric.value,
                            'timestamp': metric.timestamp.timestamp()
                        }
                    )
            
            logger.info(f"Successfully processed {len(metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Error processing metrics: {str(e)}")
            raise

    # Add to background tasks
    background_tasks.add_task(process_metrics, metrics)
    
    return {"message": f"Processing {len(metrics)} metrics"}

@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(
    events: List[EventData],
    background_tasks: BackgroundTasks,
    token = Depends(require_ingest)
):
    """
    Ingest event data.
    Events will be:
    1. Published to NATS for real-time processing
    2. Stored in QuestDB
    3. Processed by Materialize for real-time analytics
    """
    async def process_events(events: List[EventData]):
        try:
            # Get NATS client
            nc = await get_nats_client()
            
            # Publish to NATS
            for event in events:
                await nc.publish(
                    "events.raw",
                    json.dumps(event.dict()).encode()
                )
            
            # Store in QuestDB
            questdb = get_questdb_sender()
            with questdb as sender:
                for event in events:
                    sender.row(
                        "events",
                        symbols={
                            'name': event.name,
                            'source': event.source,
                            'type': event.type,
                            'event_type': event.event_type,
                            'severity': event.severity
                        },
                        columns={
                            'value': event.value,
                            'timestamp': event.timestamp.timestamp()
                        }
                    )
            
            logger.info(f"Successfully processed {len(events)} events")
            
        except Exception as e:
            logger.error(f"Error processing events: {str(e)}")
            raise

    # Add to background tasks
    background_tasks.add_task(process_events, events)
    
    return {"message": f"Processing {len(events)} events"}

@router.post("/views", response_model=MaterializedView)
async def create_materialized_view(
    view: MaterializedView,
    token = Depends(require_view_management)
):
    """Create a new materialized view for real-time analytics"""
    success = await materialize_service.create_materialized_view(view)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create materialized view"
        )
    return view

@router.post("/aggregations", response_model=MaterializedAggregation)
async def create_real_time_aggregation(
    aggregation: MaterializedAggregation,
    token = Depends(require_view_management)
):
    """Create a new real-time aggregation view"""
    success = await materialize_service.create_real_time_aggregation(aggregation)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create real-time aggregation"
        )
    return aggregation

@router.get("/metrics/{view_name}")
async def get_real_time_metrics(
    view_name: str,
    limit: int = 100,
    token = Depends(get_current_user_token)
):
    """Get real-time metrics from a materialized view"""
    metrics = await materialize_service.get_real_time_metrics(view_name, limit)
    return metrics 