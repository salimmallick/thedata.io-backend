from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class ResourceTrackingConfig(BaseModel):
    """Resource tracking configuration"""
    interval: int = Field(..., description="Tracking interval in seconds")
    retention: int = Field(..., description="Data retention period in days")

class QueryOptimizationConfig(BaseModel):
    """Query optimization configuration"""
    slow_query_threshold: float = Field(..., description="Threshold for slow queries in seconds")
    pattern_retention: int = Field(..., description="Pattern retention period in days")

class MetricsIntervalConfig(BaseModel):
    """Metrics interval configuration"""
    resource: int = Field(..., description="Resource metrics interval")
    query: int = Field(..., description="Query metrics interval")
    system: int = Field(..., description="System metrics interval")

class MetricsRetentionConfig(BaseModel):
    """Metrics retention configuration"""
    resource: int = Field(..., description="Resource metrics retention days")
    query: int = Field(..., description="Query metrics retention days")
    system: int = Field(..., description="System metrics retention days")

class AlertThresholds(BaseModel):
    """Alert threshold configuration"""
    cpu: float = Field(..., description="CPU usage threshold percentage")
    memory: float = Field(..., description="Memory usage threshold percentage")
    disk: float = Field(..., description="Disk usage threshold percentage")
    network: float = Field(..., description="Network usage threshold MB/s")

class NotificationSettings(BaseModel):
    """Notification settings configuration"""
    email: Dict[str, Any] = Field(..., description="Email notification settings")
    slack: Dict[str, Any] = Field(..., description="Slack notification settings")
    pagerduty: Dict[str, Any] = Field(..., description="PagerDuty notification settings")

class MetricsConfig(BaseModel):
    """Metrics configuration"""
    collection_enabled: bool = Field(..., description="Whether metrics collection is enabled")
    intervals: MetricsIntervalConfig
    retention: MetricsRetentionConfig

class AlertConfig(BaseModel):
    """Alert configuration"""
    enabled: bool = Field(..., description="Whether alerting is enabled")
    channels: List[str] = Field(..., description="Alert notification channels")
    thresholds: AlertThresholds
    notification_settings: NotificationSettings

class SystemConfig(BaseModel):
    """System configuration"""
    resource_tracking: ResourceTrackingConfig
    query_optimization: QueryOptimizationConfig
    metrics: MetricsConfig
    alerts: AlertConfig 