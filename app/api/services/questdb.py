from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from ..core.database import db_pool, DatabaseError

logger = logging.getLogger(__name__)

class QuestDBService:
    """Service for interacting with QuestDB."""
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against QuestDB."""
        try:
            async with db_pool.questdb_connection() as conn:
                result = await conn.fetch(query, *(params or ()))
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error executing QuestDB query: {e}")
            raise
    
    async def get_time_series_data(
        self,
        table_name: str,
        start_time: datetime,
        end_time: datetime,
        columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get time series data for a specific time range."""
        cols = ", ".join(columns) if columns else "*"
        query = f"""
        SELECT {cols}
        FROM {table_name}
        WHERE timestamp >= $1
        AND timestamp < $2
        ORDER BY timestamp
        """
        
        return await self.execute_query(query, [start_time, end_time])
    
    async def create_table(self, table_name: str, schema: Dict[str, str]) -> None:
        """Create a new table in QuestDB."""
        columns = [f"{name} {type_}" for name, type_ in schema.items()]
        query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(columns)}
        ) timestamp(timestamp)
        """
        
        await self.execute_query(query)

# Create a singleton instance
questdb_service = QuestDBService() 