from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PostgreSQL settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # ClickHouse settings
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str

    # QuestDB settings
    QUESTDB_HOST: str
    QUESTDB_PORT: int
    QUESTDB_USER: str
    QUESTDB_PASSWORD: str

    # NATS settings
    NATS_URL: str

    # Redis settings
    REDIS_URL: str

    # Materialize settings
    MATERIALIZE_URL: Optional[str] = None
    MATERIALIZE_HOST: str = "materialize"  # Default to service name
    MATERIALIZE_PORT: int = 6875  # Default Materialize port
    MATERIALIZE_USER: str = "materialize"  # Default Materialize user
    MATERIALIZE_PASSWORD: str = ""  # Default to no password
    MATERIALIZE_DB: str = "materialize"  # Default database name

    # Connection pool settings
    min_pool_size: int = 1
    max_pool_size: int = 10
    pool_timeout: int = 30

    # Cache settings
    cache_ttl: int = 300  # 5 minutes
    cache_max_size: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from the environment

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse Materialize URL if provided
        if hasattr(self, 'MATERIALIZE_URL') and self.MATERIALIZE_URL:
            from urllib.parse import urlparse
            url = urlparse(self.MATERIALIZE_URL)
            if url.hostname:
                self.MATERIALIZE_HOST = url.hostname
            if url.port:
                self.MATERIALIZE_PORT = url.port
            if url.username:
                self.MATERIALIZE_USER = url.username
            if url.password:
                self.MATERIALIZE_PASSWORD = url.password
            if url.path and url.path.strip('/'):
                self.MATERIALIZE_DB = url.path.strip('/')

settings = Settings() 