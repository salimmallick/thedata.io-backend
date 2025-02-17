from pydantic import BaseModel, Field, UUID4, EmailStr
from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime
from enum import Enum
from pydantic.types import constr

class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"

class SubscriptionTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class DataSourceType(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    SERVER = "server"
    IOT = "iot"
    CUSTOM = "custom"

class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    name: Optional[str] = None
    api_key: Optional[str] = None

class Organization(OrganizationBase):
    id: str
    api_key: str
    created_at: datetime

    class Config:
        from_attributes = True

class Organization(BaseModel):
    """Organization model for customer management"""
    org_id: UUID4
    name: str
    slug: Annotated[str, Field(pattern=r"^[a-z0-9-]+$")]
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    settings: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class APIKey(BaseModel):
    """API Key model for customer authentication"""
    key_id: UUID4
    org_id: UUID4
    name: str
    key_hash: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    status: str = "active"

    class Config:
        from_attributes = True

class RetentionPolicy(BaseModel):
    """Data retention policy for customer data"""
    policy_id: UUID4
    org_id: UUID4
    data_type: str
    retention_days: int
    archival_enabled: bool = False
    archival_days: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DataSource(BaseModel):
    """Data source configuration for customer integrations"""
    source_id: UUID4
    org_id: UUID4
    name: str
    type: DataSourceType
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UsageMetrics(BaseModel):
    """Usage metrics for customer billing"""
    org_id: UUID4
    timestamp: datetime
    metric_type: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

    class Config:
        from_attributes = True

class OrganizationLimits(BaseModel):
    """Resource limits based on subscription tier"""
    max_events_per_second: int
    max_retention_days: int
    max_data_sources: int
    max_api_keys: int
    included_storage_gb: int
    included_events_million: int
    features: List[str]

    @classmethod
    def get_tier_limits(cls, tier: SubscriptionTier) -> "OrganizationLimits":
        """Get limits for a subscription tier"""
        limits = {
            SubscriptionTier.FREE: {
                "max_events_per_second": 100,
                "max_retention_days": 30,
                "max_data_sources": 3,
                "max_api_keys": 2,
                "included_storage_gb": 10,
                "included_events_million": 1,
                "features": ["basic_analytics", "basic_monitoring"]
            },
            SubscriptionTier.STARTER: {
                "max_events_per_second": 1000,
                "max_retention_days": 90,
                "max_data_sources": 10,
                "max_api_keys": 5,
                "included_storage_gb": 100,
                "included_events_million": 10,
                "features": ["basic_analytics", "basic_monitoring", "alerts"]
            },
            SubscriptionTier.PROFESSIONAL: {
                "max_events_per_second": 10000,
                "max_retention_days": 180,
                "max_data_sources": 50,
                "max_api_keys": 20,
                "included_storage_gb": 1000,
                "included_events_million": 100,
                "features": [
                    "advanced_analytics",
                    "advanced_monitoring",
                    "alerts",
                    "custom_dashboards",
                    "video_analytics"
                ]
            },
            SubscriptionTier.ENTERPRISE: {
                "max_events_per_second": 100000,
                "max_retention_days": 365,
                "max_data_sources": -1,  # Unlimited
                "max_api_keys": -1,  # Unlimited
                "included_storage_gb": 10000,
                "included_events_million": 1000,
                "features": [
                    "advanced_analytics",
                    "advanced_monitoring",
                    "alerts",
                    "custom_dashboards",
                    "video_analytics",
                    "custom_retention",
                    "dedicated_support",
                    "sla"
                ]
            }
        }
        return cls(**limits[tier])

class OnboardingStatus(BaseModel):
    """Customer onboarding status tracking"""
    org_id: UUID4
    steps_completed: List[str]
    current_step: str
    integration_status: Dict[str, str]
    data_sources_configured: int
    has_test_data: bool
    has_production_data: bool
    support_contact: Optional[str]
    last_activity: datetime

    class Config:
        from_attributes = True 