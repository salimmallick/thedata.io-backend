from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os
from pydantic import Field

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "theData.io API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database Configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    POSTGRES_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # Database Pool Configuration
    DB_POOL_MIN_SIZE: int = Field(default=int(os.getenv("DB_POOL_MIN_SIZE", "5")), description="Minimum number of connections in the pool")
    DB_POOL_MAX_SIZE: int = Field(default=int(os.getenv("DB_POOL_MAX_SIZE", "20")), description="Maximum number of connections in the pool")
    DB_POOL_TIMEOUT: int = Field(default=int(os.getenv("DB_POOL_TIMEOUT", "30")), description="Connection timeout in seconds")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings() 