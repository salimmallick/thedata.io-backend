from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    """Application settings."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )
    
    # ClickHouse settings
    CLICKHOUSE_HOST: str = "clickhouse"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "default"
    
    # QuestDB settings
    QUESTDB_HOST: str = "questdb"
    QUESTDB_PORT: int = 8812
    QUESTDB_USER: str = "admin"
    QUESTDB_PASSWORD: str = "quest"
    QUESTDB_DATABASE: str = "qdb"
    
    # Materialize settings
    MATERIALIZE_HOST: str = "materialize"
    MATERIALIZE_PORT: int = 6875
    MATERIALIZE_USER: str = "materialize"
    MATERIALIZE_PASSWORD: str = ""
    MATERIALIZE_DATABASE: str = "materialize"
    
    # NATS settings
    NATS_HOST: str = "nats"
    NATS_PORT: int = 4222
    NATS_USER: str = ""
    NATS_PASSWORD: str = ""
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_SECURITY_PROTOCOL: str = "PLAINTEXT"
    KAFKA_SASL_MECHANISM: Optional[str] = None
    KAFKA_SASL_USERNAME: Optional[str] = None
    KAFKA_SASL_PASSWORD: Optional[str] = None
    
    # RabbitMQ settings
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = True
    API_RELOAD: bool = True
    API_WORKERS: int = 4
    
    # Auth settings
    AUTH_SECRET_KEY: str = "your-secret-key"
    AUTH_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Create settings instance
settings = Settings() 