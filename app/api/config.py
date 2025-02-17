from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    VERSION: str = "0.1.0"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database URLs
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@postgres:5432/thedata")
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    CLICKHOUSE_PORT: int = 8123
    QUESTDB_HOST: str = os.getenv("QUESTDB_HOST", "questdb")
    QUESTDB_PORT: int = 8812
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # NATS
    NATS_URL: str = os.getenv("NATS_URL", "nats://nats:4222")
    
    # Monitoring
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp"
    JAEGER_HOST: str = os.getenv("JAEGER_HOST", "jaeger")
    JAEGER_PORT: int = 6831
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: int = 1000  # requests per minute
    
    # Caching
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TIMEOUT: int = 300  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 