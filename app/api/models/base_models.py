"""
Base models for the application.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
from enum import Enum

class SubscriptionTier(str, Enum):
    """Organization subscription tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class OrganizationStatus(str, Enum):
    """Organization status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"

class DataSourceType(str, Enum):
    """Data source types."""
    WEB = "web"
    MOBILE = "mobile"
    SERVER = "server"
    IOT = "iot"
    CUSTOM = "custom"

class PipelineStatus(str, Enum):
    """Pipeline status."""
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"

class SyncStatus(str, Enum):
    """Data sync status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class BaseTimestampModel(BaseModel):
    """Base model with timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        from_attributes = True

class Organization(BaseTimestampModel):
    """Organization model."""
    org_id: UUID4
    name: str
    slug: str
    api_key: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    settings: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DataSource(BaseTimestampModel):
    """Data source model."""
    source_id: UUID4
    org_id: UUID4
    name: str
    type: DataSourceType
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    health: str = "unknown"
    last_sync_at: Optional[datetime] = None

class Pipeline(BaseTimestampModel):
    """Pipeline model."""
    pipeline_id: UUID4
    org_id: UUID4
    name: str
    description: Optional[str] = None
    status: PipelineStatus = PipelineStatus.ACTIVE
    config: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[Dict[str, Any]] = None
    health: str = "unknown"
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

class PipelineStep(BaseTimestampModel):
    """Pipeline step model."""
    step_id: UUID4
    pipeline_id: UUID4
    name: str
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    order_index: int
    enabled: bool = True

class PipelineRun(BaseTimestampModel):
    """Pipeline run model."""
    run_id: UUID4
    pipeline_id: UUID4
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

class TransformationRule(BaseTimestampModel):
    """Transformation rule model."""
    rule_id: UUID4
    org_id: UUID4
    name: str
    description: Optional[str] = None
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    version: int = 1

class DataSync(BaseTimestampModel):
    """Data sync model."""
    sync_id: UUID4
    org_id: UUID4
    source_id: UUID4
    pipeline_id: Optional[UUID4] = None
    status: SyncStatus = SyncStatus.PENDING
    records_processed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict) 