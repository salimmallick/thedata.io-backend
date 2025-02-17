from typing import List, Dict, Any, Optional
from datetime import datetime
import clickhouse_driver
import logging
from ..core.monitoring.config import settings

logger = logging.getLogger(__name__)

class ClickhouseService:
    """Service for interacting with ClickHouse database."""
    
    def __init__(self):
        """Initialize ClickHouse service."""
        client_params = {
            'host': settings.CLICKHOUSE_HOST,
            'port': settings.CLICKHOUSE_PORT,
            'user': settings.CLICKHOUSE_USER,
            'database': settings.CLICKHOUSE_DATABASE
        }
        
        # Only add password for non-test environments
        if settings.ENVIRONMENT != "test":
            client_params['password'] = settings.CLICKHOUSE_PASSWORD
        
        self.client = clickhouse_driver.Client(**client_params)
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against ClickHouse."""
        try:
            result = self.client.execute(query, params or {}, with_column_types=True)
            rows, columns = result
            
            # Convert rows to dictionaries with column names
            column_names = [col[0] for col in columns]
            return [dict(zip(column_names, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error executing ClickHouse query: {e}")
            raise
    
    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get metrics data for a specific time range."""
        query = """
        SELECT
            timestamp,
            name,
            value,
            tags
        FROM metrics
        WHERE timestamp >= %(start_time)s
        AND timestamp < %(end_time)s
        """
        
        if metric_names:
            query += " AND name IN %(metric_names)s"
        
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "metric_names": metric_names
        }
        
        return await self.execute_query(query, params)
    
    async def get_events(
        self,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[List[str]] = None,
        severity: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get events data for a specific time range."""
        query = """
        SELECT
            timestamp,
            name,
            event_type,
            severity,
            tags,
            payload
        FROM events
        WHERE timestamp >= %(start_time)s
        AND timestamp < %(end_time)s
        """
        
        if event_types:
            query += " AND event_type IN %(event_types)s"
        if severity:
            query += " AND severity IN %(severity)s"
        
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "event_types": event_types,
            "severity": severity
        }
        
        return await self.execute_query(query, params)

# Create a singleton instance
clickhouse_service = ClickhouseService() 