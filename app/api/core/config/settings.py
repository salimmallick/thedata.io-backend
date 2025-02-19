"""
Application settings and configuration.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
import os
from pydantic import Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Service Settings
    SERVICE_NAME: str = Field(default="data-sync-api", description="Name of the service")
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "theData.io API"
    PROJECT_DESCRIPTION: str = "Data Synchronization and Analytics API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Changed from 8 days to 30 minutes
    
    # Tracing Settings
    TRACING_ENABLED: bool = Field(default=True, description="Enable distributed tracing")
    OTLP_ENDPOINT: str = Field(
        default="http://jaeger:4317",
        description="OpenTelemetry collector endpoint",
        env="OTLP_ENDPOINT"
    )
    OTLP_SECURE: bool = Field(
        default=False,
        description="Use secure connection for OTLP exporter",
        env="OTLP_SECURE"
    )
    TRACE_EXCLUDED_URLS: List[str] = Field(
        default=["health", "metrics"],
        description="URLs to exclude from tracing"
    )
    
    # Database URLs and Connection Settings
    POSTGRES_DSN: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/thedataio",
        description="PostgreSQL connection string",
        env="POSTGRES_DSN"
    )
    POSTGRES_MIN_POOL_SIZE: int = Field(default=5, description="Minimum number of connections in the pool")
    POSTGRES_MAX_POOL_SIZE: int = Field(default=20, description="Maximum number of connections in the pool")
    
    REDIS_DSN: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
        env="REDIS_DSN"
    )
    
    CLICKHOUSE_URL: str = Field(
        default="clickhouse://localhost:9000",
        description="ClickHouse connection string",
        env="CLICKHOUSE_URL"
    )
    QUESTDB_URL: str = Field(
        default="http://localhost:9000",
        description="QuestDB connection string",
        env="QUESTDB_URL"
    )
    NATS_URL: str = Field(
        default="nats://localhost:4222",
        description="NATS connection string",
        env="NATS_URL"
    )
    
    # Database Settings
    CLICKHOUSE_HOST: str = Field(
        default="localhost",
        description="ClickHouse host",
        env="CLICKHOUSE_HOST"
    )
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "9000"))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "default")
    
    QUESTDB_HOST: str = os.getenv("QUESTDB_HOST", "localhost")
    QUESTDB_PORT: int = int(os.getenv("QUESTDB_PORT", "9000"))
    
    # Monitoring Settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE_PATH: str = Field(default="logs/app.log", env="LOG_FILE_PATH")
    LOG_ROTATION_SIZE: int = Field(default=10485760, env="LOG_ROTATION_SIZE")  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8000"))
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost"
    ]
    
    # Default admin settings
    DEFAULT_ADMIN_EMAIL: str = "admin@thedata.io"
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    
    class Config:
        """Pydantic config."""
        case_sensitive = True
        env_file = ".env"
        from_attributes = True  # Replaces orm_mode in Pydantic v2

# Create global settings instance
settings = Settings()

__all__ = ['settings', 'Settings'] 