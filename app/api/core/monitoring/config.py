"""
Monitoring configuration settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field

class MonitoringSettings(BaseSettings):
    """Monitoring configuration settings."""
    
    # Service settings
    SERVICE_NAME: str = Field(default="thedata-api", description="Name of the service for monitoring")
    ENVIRONMENT: str = Field(default="development", description="Environment (development, staging, production)")
    
    # Prometheus settings
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    PROMETHEUS_PORT: int = Field(default=9090, description="Port for Prometheus metrics server")
    PROMETHEUS_HOST: str = Field(default="0.0.0.0", description="Host for Prometheus metrics server")
    
    # Tracing settings
    JAEGER_HOST: str = Field(default="jaeger", description="Jaeger host")
    JAEGER_PORT: int = Field(default=6831, description="Jaeger port")
    JAEGER_ENABLED: bool = Field(default=True, description="Enable Jaeger tracing")
    
    # Health check settings
    HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Health check interval in seconds")
    
    # Metric collection settings
    METRIC_COLLECTION_INTERVAL: int = Field(default=30, description="Metric collection interval in seconds")
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False

settings = MonitoringSettings()

__all__ = ['settings', 'MonitoringSettings'] 