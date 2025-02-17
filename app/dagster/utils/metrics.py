from typing import List, Dict, Any
from datetime import datetime, timedelta
from ...api.services.materialize import materialize_service
import logging

logger = logging.getLogger(__name__)

async def get_performance_metrics(start_time: datetime, end_time: datetime) -> Dict[str, List[float]]:
    """Get performance metrics for a given time range."""
    try:
        query = """
        SELECT metric_name, value, timestamp
        FROM performance_metrics
        WHERE timestamp >= $1 AND timestamp < $2
        ORDER BY timestamp ASC
        """
        
        results = await materialize_service.execute_query(
            query,
            {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
        )
        
        # Group metrics by name
        metrics_by_name = {}
        for row in results:
            metric_name = row["metric_name"]
            if metric_name not in metrics_by_name:
                metrics_by_name[metric_name] = []
            metrics_by_name[metric_name].append(float(row["value"]))
        
        return metrics_by_name
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return {}

async def get_video_metrics(start_time: datetime, end_time: datetime) -> Dict[str, List[float]]:
    """Get video quality metrics for a given time range."""
    try:
        query = """
        SELECT metric_name, value, timestamp
        FROM video_metrics
        WHERE timestamp >= $1 AND timestamp < $2
        ORDER BY timestamp ASC
        """
        
        results = await materialize_service.execute_query(
            query,
            {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
        )
        
        # Group metrics by name
        metrics_by_name = {}
        for row in results:
            metric_name = row["metric_name"]
            if metric_name not in metrics_by_name:
                metrics_by_name[metric_name] = []
            metrics_by_name[metric_name].append(float(row["value"]))
        
        return metrics_by_name
    except Exception as e:
        logger.error(f"Error getting video metrics: {str(e)}")
        return {} 