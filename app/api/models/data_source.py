"""
Data source models.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

class DataSourceType(str, Enum):
    """Supported data source types."""
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    QUESTDB = "questdb"
    REDIS = "redis"
    NATS = "nats"

class DataSourceStatus(str, Enum):
    """Data source status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"

class DataSourceHealth(str, Enum):
    """Data source health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

class ConnectionConfig(BaseModel):
    """Data source connection configuration."""
    host: str = Field(..., description="Host address")
    port: int = Field(..., description="Port number", ge=1, le=65535)
    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    database: Optional[str] = Field(None, description="Database name")
    ssl_enabled: bool = Field(False, description="Whether SSL is enabled")
    connection_timeout: int = Field(30, description="Connection timeout in seconds", ge=1, le=300)
    additional_params: Optional[Dict[str, Any]] = Field(None, description="Additional connection parameters")

    @validator("port")
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @validator("connection_timeout")
    def validate_timeout(cls, v):
        """Validate connection timeout."""
        if not 1 <= v <= 300:
            raise ValueError("Connection timeout must be between 1 and 300 seconds")
        return v

class DataSourceConfig(BaseModel):
    """Data source configuration."""
    connection: ConnectionConfig
    sync_schedule: Optional[str] = Field(None, description="Cron expression for sync schedule")
    retention_days: Optional[int] = Field(None, description="Data retention period in days")
    max_connections: Optional[int] = Field(None, description="Maximum number of connections")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

class DataSourceMetrics(BaseModel):
    """Data source metrics."""
    latency: float = Field(..., description="Average latency in milliseconds")
    error_rate: float = Field(..., description="Error rate percentage")
    success_rate: float = Field(..., description="Success rate percentage")
    total_records: int = Field(..., description="Total number of records processed")
    sync_duration: float = Field(..., description="Last sync duration in seconds")
    last_sync: datetime = Field(..., description="Last sync timestamp")

class DataSourceValidationResult(BaseModel):
    """Data source validation result."""
    is_valid: bool = Field(..., description="Whether the validation was successful")
    status: DataSourceStatus = Field(..., description="Data source status after validation")
    health: DataSourceHealth = Field(..., description="Data source health after validation")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    validation_details: Optional[Dict[str, Any]] = Field(None, description="Additional validation details")

class DataSourceCreate(BaseModel):
    """Data source creation model."""
    name: str = Field(..., description="Data source name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Data source description")
    type: DataSourceType = Field(..., description="Data source type")
    config: DataSourceConfig = Field(..., description="Data source configuration")
    organization_id: str = Field(..., description="Organization ID")

class DataSourceUpdate(BaseModel):
    """Data source update model."""
    name: Optional[str] = Field(None, description="Data source name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Data source description")
    config: Optional[DataSourceConfig] = Field(None, description="Data source configuration")
    status: Optional[DataSourceStatus] = Field(None, description="Data source status")

class DataSource(BaseModel):
    """Data source model."""
    id: str = Field(..., description="Data source ID")
    name: str = Field(..., description="Data source name")
    description: Optional[str] = Field(None, description="Data source description")
    type: DataSourceType = Field(..., description="Data source type")
    config: DataSourceConfig = Field(..., description="Data source configuration")
    status: DataSourceStatus = Field(..., description="Data source status")
    health: DataSourceHealth = Field(..., description="Data source health")
    organization_id: str = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metrics: Optional[DataSourceMetrics] = Field(None, description="Latest metrics") 