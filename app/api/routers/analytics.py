from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..services.materialize import materialize_service
from ..core.database import db_pool
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics"])

# Permission checkers
require_analytics = PermissionChecker(["view_analytics"])
require_admin = PermissionChecker(["admin"])

@router.get("/realtime/{view_name}")
async def get_realtime_metrics(
    view_name: str,
    token = Depends(require_analytics)
):
    """Get realtime metrics from a view"""
    metrics = await materialize_service.get_real_time_metrics(view_name)
    return {
        "view": view_name,
        "timestamp": datetime.utcnow(),
        "metrics": metrics
    }

@router.get("/historical/{table_name}")
async def get_historical_data(
    table_name: str,
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    aggregation: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    token = Depends(require_analytics)
):
    """Get historical data from ClickHouse"""
    try:
        async with db_pool.clickhouse_connection() as client:
            # Build query based on parameters
            where_clauses = [
                f"timestamp >= '{start_time}'",
                f"timestamp < '{end_time}'"
            ]
            
            if filters:
                for key, value in filters.items():
                    where_clauses.append(f"{key} = '{value}'")
            
            where_clause = " AND ".join(where_clauses)
            
            if aggregation:
                query = f"""
                    SELECT
                        toStartOfHour(timestamp) as hour,
                        count(*) as event_count,
                        {aggregation}
                    FROM {table_name}
                    WHERE {where_clause}
                    GROUP BY hour
                    ORDER BY hour
                """
            else:
                query = f"""
                    SELECT *
                    FROM {table_name}
                    WHERE {where_clause}
                    ORDER BY timestamp
                """
            
            results = client.execute(query)
            return {
                "table": table_name,
                "start_time": start_time,
                "end_time": end_time,
                "data": results
            }
            
    except Exception as e:
        logger.error(f"Error querying historical data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error querying historical data"
        )

@router.get("/metrics/{metric_name}")
async def get_timeseries_metrics(
    metric_name: str,
    token = Depends(require_analytics)
):
    """Get timeseries metrics"""
    try:
        async with db_pool.questdb_connection() as sender:
            query = f"""
                SELECT
                    timestamp,
                    metric_name,
                    avg(value) as avg_value,
                    min(value) as min_value,
                    max(value) as max_value
                FROM metrics
                WHERE
                    metric_name = '{metric_name}'
                SAMPLE BY 1m
                ALIGN TO CALENDAR
            """
            
            results = sender.execute(query)
            return {
                "metric": metric_name,
                "data": results
            }
            
    except Exception as e:
        logger.error(f"Error querying time-series metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error querying time-series metrics"
        )

@router.post("/views")
async def create_custom_view(
    view_name: str,
    query: str,
    refresh_interval: Optional[int] = 60,
    token = Depends(require_admin)
):
    """Create a custom materialized view"""
    success = await materialize_service.create_materialized_view(
        name=view_name,
        query=query,
        refresh_interval=f"{refresh_interval} seconds"
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create materialized view"
        )
    
    return {
        "status": "success",
        "view": view_name,
        "refresh_interval": refresh_interval
    } 