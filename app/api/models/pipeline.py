"""
Pipeline models with validation.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

class PipelineType(str, Enum):
    """Pipeline types."""
    ETL = "etl"
    STREAMING = "streaming"
    BATCH = "batch"
    REAL_TIME = "real_time"
    CUSTOM = "custom"

class PipelineStatus(str, Enum):
    """Pipeline status values."""
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    COMPLETED = "completed"
    PAUSED = "paused"

class PipelineHealth(str, Enum):
    """Pipeline health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    source_config: Dict[str, Any] = Field(..., description="Source configuration")
    destination_config: Dict[str, Any] = Field(..., description="Destination configuration")
    transformation_rules: Optional[List[Dict[str, Any]]] = Field(None, description="Data transformation rules")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="Scheduling configuration")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry policy configuration")
    monitoring_config: Optional[Dict[str, Any]] = Field(None, description="Monitoring configuration")

    @validator("source_config")
    def validate_source_config(cls, v):
        """Validate source configuration."""
        required_fields = ["type", "connection_details"]
        if not all(field in v for field in required_fields):
            raise ValueError(f"Source config must contain: {required_fields}")
        return v

    @validator("destination_config")
    def validate_destination_config(cls, v):
        """Validate destination configuration."""
        required_fields = ["type", "connection_details"]
        if not all(field in v for field in required_fields):
            raise ValueError(f"Destination config must contain: {required_fields}")
        return v

class PipelineMetrics(BaseModel):
    """Pipeline performance metrics."""
    throughput: float = Field(..., description="Records processed per second")
    latency: float = Field(..., description="Average processing latency in milliseconds")
    error_rate: float = Field(..., description="Error rate as percentage")
    success_rate: float = Field(..., description="Success rate as percentage")
    processed_records: int = Field(..., description="Total records processed")
    failed_records: int = Field(..., description="Total failed records")

class PipelineBase(BaseModel):
    """Base pipeline model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    type: PipelineType
    config: PipelineConfig
    schedule: Optional[str] = Field(None, description="Cron expression for scheduling")

    @validator("schedule")
    def validate_schedule(cls, v):
        """Validate cron schedule expression."""
        if v:
            # Add cron expression validation if needed
            pass
        return v

class PipelineCreate(PipelineBase):
    """Pipeline creation model."""
    data_source_id: int = Field(..., gt=0)

class PipelineUpdate(BaseModel):
    """Pipeline update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    type: Optional[PipelineType] = None
    config: Optional[PipelineConfig] = None
    schedule: Optional[str] = None
    status: Optional[PipelineStatus] = None

class Pipeline(PipelineBase):
    """Complete pipeline model."""
    id: int
    organization_id: int
    data_source_id: int
    status: PipelineStatus
    health: PipelineHealth
    version: str
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime] = None

    class Config:
        """Pydantic config."""
        orm_mode = True

class PipelineStatusResponse(BaseModel):
    """Pipeline status response."""
    status: PipelineStatus
    health: PipelineHealth
    metrics: Optional[PipelineMetrics] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    error: Optional[str] = None

class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class PipelineLog(BaseModel):
    """Pipeline log entry."""
    timestamp: datetime
    level: LogLevel
    message: str
    details: Optional[Dict[str, Any]] = None

class PipelineLogs(BaseModel):
    """Pipeline logs response."""
    logs: List[PipelineLog]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_entries: int 