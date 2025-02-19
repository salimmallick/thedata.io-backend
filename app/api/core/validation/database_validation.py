"""
Database validation module.
"""
from typing import Dict, Any, Optional
import logging
from ..instances import db_pool, metrics
from ..monitoring.base_metrics import BaseMetrics

logger = logging.getLogger(__name__)

class DatabaseValidator:
    """Validates database operations and connections."""
    
    def __init__(self):
        self.validation_errors = []
    
    async def validate_connection(self, database: str) -> bool:
        """Validate database connection."""
        if not db_pool:
            logger.error("Database pool not initialized")
            return False
            
        try:
            if database == "postgres":
                async with db_pool.get_postgres_conn() as conn:
                    await conn.execute("SELECT 1")
            elif database == "clickhouse":
                async with db_pool.get_clickhouse_client() as client:
                    client.command("SELECT 1")
            elif database == "questdb":
                async with db_pool.get_questdb_sender() as sender:
                    await sender.ping()
            elif database == "nats":
                async with db_pool.get_nats_client() as nc:
                    await nc.ping()
            elif database == "redis":
                async with db_pool.redis_connection() as redis:
                    await redis.ping()
            else:
                logger.error(f"Unknown database type: {database}")
                return False
                
            metrics.track_component_health(f"{database}_connection", True)
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate {database} connection: {str(e)}")
            metrics.track_component_health(f"{database}_connection", False)
            self.validation_errors.append({
                "database": database,
                "error": str(e)
            })
            return False
    
    async def validate_query(self, database: str, query: str) -> Dict[str, Any]:
        """Validate database query."""
        if not db_pool:
            return {"valid": False, "error": "Database pool not initialized"}
            
        try:
            if database == "postgres":
                async with db_pool.get_postgres_conn() as conn:
                    # Explain query plan
                    plan = await conn.fetch(f"EXPLAIN {query}")
                    return {
                        "valid": True,
                        "plan": [row[0] for row in plan]
                    }
            elif database == "clickhouse":
                async with db_pool.get_clickhouse_client() as client:
                    plan = client.command(f"EXPLAIN {query}")
                    return {
                        "valid": True,
                        "plan": plan
                    }
            else:
                return {
                    "valid": False,
                    "error": f"Query validation not supported for {database}"
                }
                
        except Exception as e:
            logger.error(f"Query validation failed for {database}: {str(e)}")
            self.validation_errors.append({
                "database": database,
                "query": query,
                "error": str(e)
            })
            return {
                "valid": False,
                "error": str(e)
            }
    
    def get_validation_errors(self) -> list:
        """Get list of validation errors."""
        return self.validation_errors
    
    def clear_validation_errors(self):
        """Clear validation errors."""
        self.validation_errors = [] 