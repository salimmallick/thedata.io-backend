from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from ..core.database import db_pool, DatabaseError

logger = logging.getLogger(__name__)

class ClickhouseService:
    """Service for interacting with ClickHouse database."""
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against ClickHouse."""
        try:
            async with db_pool.clickhouse_connection() as client:
                result = await client.execute(query, params or {}, with_column_types=True)
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