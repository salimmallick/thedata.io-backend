from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
import logging
from ...config import settings

logger = logging.getLogger(__name__)

class QuestDBService:
    """Service for interacting with QuestDB."""
    
    def __init__(self):
        """Initialize QuestDB service."""
        self.conn_params = {
            'host': settings.QUESTDB_HOST,
            'port': settings.QUESTDB_PORT,
            'user': settings.QUESTDB_USER,
            'password': settings.QUESTDB_PASSWORD,
            'database': settings.QUESTDB_DATABASE
        }
    
    def get_connection(self):
        """Get a connection to QuestDB."""
        return psycopg2.connect(**self.conn_params)
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query against QuestDB."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or {})
                    if cur.description:
                        columns = [desc[0] for desc in cur.description]
                        return [dict(zip(columns, row)) for row in cur.fetchall()]
                    return []
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
        WHERE timestamp >= %s
        AND timestamp < %s
        ORDER BY timestamp
        """
        
        return await self.execute_query(query, (start_time, end_time))
    
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