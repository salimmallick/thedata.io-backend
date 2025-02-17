from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for monitoring and tracing."""
    JAEGER_HOST: str = "jaeger"
    JAEGER_PORT: int = 6831
    JAEGER_ENABLED: bool = True
    SERVICE_NAME: str = "thedata-api"
    ENVIRONMENT: str = "development"

    # ClickHouse settings
    CLICKHOUSE_HOST: str = "clickhouse"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "default"

    class Config:
        case_sensitive = False
        extra = "allow"


settings = Settings() 