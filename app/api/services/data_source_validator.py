"""
Data source validation service.
"""
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from ..models.data_source import (
    DataSourceType,
    DataSourceStatus,
    DataSourceHealth,
    DataSourceValidationResult,
    ConnectionConfig
)
from ..core.database import db_pool, DatabaseError
from ..core.monitoring.instances import metrics

logger = logging.getLogger(__name__)

class DataSourceValidator:
    """Validator for data source connections."""

    async def _validate_postgresql(self, config: Dict[str, Any]) -> DataSourceValidationResult:
        """Validate PostgreSQL connection."""
        try:
            conn_config = ConnectionConfig(**config["connection"])
            
            # Attempt to connect
            async with db_pool.postgres_connection() as conn:
                # Test connection with simple query
                await conn.execute("SELECT 1")
                
                # Get database info
                db_info = await conn.fetchrow("""
                    SELECT 
                        current_database() as database,
                        version() as version,
                        current_timestamp as server_time
                """)
                
                return DataSourceValidationResult(
                    is_valid=True,
                    status=DataSourceStatus.ACTIVE,
                    health=DataSourceHealth.HEALTHY,
                    validation_details={
                        "database": db_info["database"],
                        "version": db_info["version"],
                        "server_time": db_info["server_time"]
                    }
                )
                
        except Exception as e:
            logger.error(f"PostgreSQL validation error: {str(e)}")
            metrics.track_error("postgresql_validation_error", str(e))
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNHEALTHY,
                error_message=str(e)
            )

    async def _validate_clickhouse(self, config: Dict[str, Any]) -> DataSourceValidationResult:
        """Validate ClickHouse connection."""
        try:
            conn_config = ConnectionConfig(**config["connection"])
            
            async with db_pool.clickhouse_connection() as client:
                # Test connection
                result = client.command("SELECT version()")
                system_info = client.command("SELECT * FROM system.build_options LIMIT 1")
                
                return DataSourceValidationResult(
                    is_valid=True,
                    status=DataSourceStatus.ACTIVE,
                    health=DataSourceHealth.HEALTHY,
                    validation_details={
                        "version": result,
                        "build_info": system_info,
                        "server_time": datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"ClickHouse validation error: {str(e)}")
            metrics.track_error("clickhouse_validation_error", str(e))
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNHEALTHY,
                error_message=str(e)
            )

    async def _validate_questdb(self, config: Dict[str, Any]) -> DataSourceValidationResult:
        """Validate QuestDB connection."""
        try:
            conn_config = ConnectionConfig(**config["connection"])
            
            async with db_pool.questdb_connection() as sender:
                # Test connection by sending a ping
                await sender.ping()
                
                return DataSourceValidationResult(
                    is_valid=True,
                    status=DataSourceStatus.ACTIVE,
                    health=DataSourceHealth.HEALTHY,
                    validation_details={
                        "connection_type": "ILP",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"QuestDB validation error: {str(e)}")
            metrics.track_error("questdb_validation_error", str(e))
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNHEALTHY,
                error_message=str(e)
            )

    async def _validate_redis(self, config: Dict[str, Any]) -> DataSourceValidationResult:
        """Validate Redis connection."""
        try:
            conn_config = ConnectionConfig(**config["connection"])
            
            async with db_pool.redis_connection() as redis:
                # Test connection
                info = await redis.info()
                
                return DataSourceValidationResult(
                    is_valid=True,
                    status=DataSourceStatus.ACTIVE,
                    health=DataSourceHealth.HEALTHY,
                    validation_details={
                        "version": info["redis_version"],
                        "connected_clients": info["connected_clients"],
                        "used_memory_human": info["used_memory_human"]
                    }
                )
                
        except Exception as e:
            logger.error(f"Redis validation error: {str(e)}")
            metrics.track_error("redis_validation_error", str(e))
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNHEALTHY,
                error_message=str(e)
            )

    async def _validate_nats(self, config: Dict[str, Any]) -> DataSourceValidationResult:
        """Validate NATS connection."""
        try:
            conn_config = ConnectionConfig(**config["connection"])
            
            async with db_pool.nats_connection() as nc:
                # Test connection with ping
                await nc.ping()
                
                # Get server info
                server_info = nc.connected_server_info
                
                return DataSourceValidationResult(
                    is_valid=True,
                    status=DataSourceStatus.ACTIVE,
                    health=DataSourceHealth.HEALTHY,
                    validation_details={
                        "server": server_info.server_id,
                        "version": server_info.version,
                        "protocol": server_info.proto,
                        "client_id": nc.client_id,
                        "max_payload": server_info.max_payload
                    }
                )
                
        except Exception as e:
            logger.error(f"NATS validation error: {str(e)}")
            metrics.track_error("nats_validation_error", str(e))
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNHEALTHY,
                error_message=str(e)
            )

    async def validate(self, source_type: str, config: Dict[str, Any]) -> DataSourceValidationResult:
        """Validate data source connection based on type."""
        validation_methods = {
            DataSourceType.POSTGRESQL.value: self._validate_postgresql,
            DataSourceType.CLICKHOUSE.value: self._validate_clickhouse,
            DataSourceType.QUESTDB.value: self._validate_questdb,
            DataSourceType.REDIS.value: self._validate_redis,
            DataSourceType.NATS.value: self._validate_nats
        }
        
        if source_type not in validation_methods:
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNKNOWN,
                error_message=f"Unsupported data source type: {source_type}"
            )
            
        try:
            # Add timeout to validation
            return await asyncio.wait_for(
                validation_methods[source_type](config),
                timeout=config["connection"].get("connection_timeout", 30)
            )
        except asyncio.TimeoutError:
            logger.error(f"Validation timeout for {source_type}")
            metrics.track_error(f"{source_type}_validation_timeout", "Connection timeout")
            return DataSourceValidationResult(
                is_valid=False,
                status=DataSourceStatus.ERROR,
                health=DataSourceHealth.UNHEALTHY,
                error_message="Connection timeout"
            )

# Create global validator instance
data_source_validator = DataSourceValidator() 