from functools import lru_cache
from typing import List, Optional, Union, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os
from pydantic import field_validator, Field, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from pydantic import GetJsonSchemaHandler

class CorsOriginsList(List[str]):
    """Custom type for CORS origins list."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler,
    ) -> CoreSchema:
        def validate_cors_origins(value: Any) -> List[str]:
            # Handle empty values
            if not value or value == "":
                return ["http://localhost:3000"]
                
            if isinstance(value, str):
                if value.startswith("["):
                    try:
                        # Try parsing as JSON array
                        origins = json.loads(value)
                        if isinstance(origins, list):
                            return [str(origin) for origin in origins if origin]
                    except json.JSONDecodeError:
                        pass
                # Try parsing as comma-separated string
                if "," in value:
                    return [origin.strip() for origin in value.split(",") if origin.strip()]
                # Single URL
                return [value.strip()] if value.strip() else ["http://localhost:3000"]
            
            if isinstance(value, list):
                return [str(origin) for origin in value if origin]
                
            return ["http://localhost:3000"]

        return core_schema.no_info_plain_validator_function(
            function=validate_cors_origins,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: x,
                return_schema=core_schema.list_schema(
                    items_schema=core_schema.str_schema()
                ),
                when_used='json'
            ),
        )

class Settings(BaseSettings):
    """Application settings."""
    
    # Core settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "TheData.io Platform"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "test-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_SECRET_KEY: str = "test-jwt-key"
    IP_WHITELIST: List[str] = ["127.0.0.1", "localhost", "0.0.0.0"]
    IP_BLACKLIST: List[str] = []
    
    # Database settings
    POSTGRES_USER: str = "test"
    POSTGRES_PASSWORD: str = "test"
    POSTGRES_HOST: str = "postgres-test"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "testdb"
    POSTGRES_URL: str = ""
    
    # Redis settings
    REDIS_URL: str = "redis://redis:6379/0"
    
    # ClickHouse settings
    CLICKHOUSE_HOST: str = "clickhouse-test"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_DATABASE: str = "default"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    
    # QuestDB settings
    QUESTDB_HOST: str = "questdb-test"
    QUESTDB_PORT: int = 8812
    QUESTDB_USER: str = "admin"
    QUESTDB_PASSWORD: str = "quest"
    QUESTDB_DATABASE: str = "questdb"
    
    # NATS settings
    NATS_URL: str = "nats://nats-test:4222"
    NATS_AUTH_TOKEN: str = "devtoken123"
    
    # CORS settings
    CORS_ORIGINS_RAW: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
        description="List of allowed CORS origins"
    )
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Logging settings
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "json"
    
    # Feature flags
    ENABLE_METRICS: bool = True
    ENABLE_TRACING: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_ANOMALY_DETECTION: bool = True
    ENABLE_SESSION_TRACKING: bool = True
    ENABLE_DATA_QUALITY_CHECKS: bool = True
    ENABLE_AUTO_SCALING: bool = True
    
    # Rate limiting
    API_RATE_LIMIT: int = 1000
    API_RATE_WINDOW: int = 60
    
    # NATS settings
    NATS_MAX_CONNECTIONS: int = 1000
    NATS_MAX_SUBSCRIPTIONS: int = 10000
    
    # Memory limits
    MATERIALIZE_MEMORY_LIMIT: str = "4GB"
    CLICKHOUSE_MEMORY_LIMIT: str = "8GB"
    QUESTDB_MEMORY_LIMIT: str = "4GB"
    NATS_MEMORY_LIMIT: str = "2GB"
    POSTGRES_MEMORY_LIMIT: str = "2GB"
    GRAFANA_MEMORY_LIMIT: str = "1GB"
    
    # Backup settings
    BACKUP_RETENTION_DAYS: int = 7
    BACKUP_S3_BUCKET: str = "thedata-backups"
    
    # AWS settings
    AWS_ACCESS_KEY_ID: str = "changeme"
    AWS_SECRET_ACCESS_KEY: str = "changeme"
    AWS_DEFAULT_REGION: str = "us-west-2"
    
    # Alertmanager settings
    ALERTMANAGER_SMTP_HOST: str = "smtp.gmail.com"
    ALERTMANAGER_SMTP_PORT: int = 587
    ALERTMANAGER_SMTP_USER: str = "alerts@thedata.io"
    ALERTMANAGER_SMTP_PASSWORD: str = "changeme123"
    
    # SSL settings
    SSL_EMAIL: str = "admin@thedata.io"
    SSL_COUNTRY: str = "US"
    SSL_STATE: str = "California"
    SSL_LOCALITY: str = "San Francisco"
    SSL_ORGANIZATION: str = "theData.io"
    SSL_ORGANIZATIONAL_UNIT: str = "Engineering"
    SSL_COMMON_NAME: str = "thedata.io"
    
    # Passwords
    SYSTEM_PASSWORD: str = "devsystem123"
    ADMIN_PASSWORD: str = "devadmin123"
    CLIENT_PASSWORD: str = "devclient123"
    GRAFANA_ADMIN_PASSWORD: str = "changeme123"
    
    # Other settings
    CLUSTER_ADVERTISE: str = "localhost"
    GF_INSTALL_PLUGINS: str = "grafana-clickhouse-datasource,grafana-worldmap-panel"
    PROMETHEUS_RETENTION_TIME: str = "15d"
    JAEGER_HOST: str = "localhost"
    JAEGER_PORT: int = 6831
    JAEGER_AGENT_HOST: str = "localhost"
    JAEGER_AGENT_PORT: int = 6831
    
    # Dagster settings
    DAGSTER_DB_USER: str = "dagster"
    DAGSTER_DB_PASSWORD: str = "changeme123"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
        validate_default=True,
        json_schema_extra={
            "example": {
                "ENVIRONMENT": "development",
                "DEBUG": True,
                "API_V1_STR": "/api/v1"
            }
        }
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_urls()
        self._init_cors()
    
    def _init_urls(self) -> None:
        """Initialize database URLs."""
        # PostgreSQL URL
        if not self.POSTGRES_URL:
            self.POSTGRES_URL = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
    
    def _init_cors(self) -> None:
        """Initialize CORS settings."""
        # Ensure BACKEND_CORS_ORIGINS matches CORS_ORIGINS
        self.BACKEND_CORS_ORIGINS = self.CORS_ORIGINS.copy()
    
    def __str__(self) -> str:
        """Return string representation with hidden secrets."""
        attrs = []
        for key, value in self.__dict__.items():
            if key.upper().endswith(("KEY", "PASSWORD", "SECRET", "TOKEN")):
                attrs.append(f"{key}=<hidden>")
            else:
                attrs.append(f"{key}={value!r}")
        return " ".join(attrs)

    @field_validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production", "test"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of {valid_envs}")
        return v.lower()

    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse and return CORS origins."""
        if not self.CORS_ORIGINS_RAW or self.CORS_ORIGINS_RAW == "":
            return ["http://localhost:3000"]
            
        if self.CORS_ORIGINS_RAW.startswith("["):
            try:
                # Try parsing as JSON array
                origins = json.loads(self.CORS_ORIGINS_RAW)
                if isinstance(origins, list):
                    return [str(origin) for origin in origins if origin]
            except json.JSONDecodeError:
                pass
        
        # Try parsing as comma-separated string
        if "," in self.CORS_ORIGINS_RAW:
            return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]
        
        # Single URL
        return [self.CORS_ORIGINS_RAW.strip()] if self.CORS_ORIGINS_RAW.strip() else ["http://localhost:3000"]

@lru_cache()
def get_settings() -> Settings:
    """Get settings instance (cached)."""
    return Settings()

# Create a global settings instance
settings = get_settings() 