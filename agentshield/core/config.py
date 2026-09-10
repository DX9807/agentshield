"""Configuration management using Pydantic Settings."""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator, AnyUrl
import secrets


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "AgentShield"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: AnyUrl = Field(
        default="postgresql+asyncpg://agentshield:agentshield@postgres:5432/agentshield"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: AnyUrl = Field(default="redis://redis:6379/0")
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_SECURITY_EVENTS_TOPIC: str = "agentshield-security-events"
    KAFKA_CONSUMER_GROUP: str = "agentshield-group"
    KAFKA_AUTO_CREATE_TOPICS: bool = True
    
    # OpenSearch
    OPENSEARCH_HOSTS: str = "http://opensearch:9200"
    OPENSEARCH_INDEX: str = "agentshield-events"
    OPENSEARCH_SSL_VERIFY: bool = False
    
    # JWT
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30
    AGENT_TOKEN_EXPIRATION_MINUTES: int = 60
    
    # Gateway
    GATEWAY_DEFAULT_TIMEOUT: int = 30
    GATEWAY_MAX_BODY_SIZE: int = 10_485_760  # 10MB
    GATEWAY_REQUEST_TIMEOUT: int = 60
    GATEWAY_ALLOWED_DOMAINS: List[str] = ["localhost", "127.0.0.1"]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    RATE_LIMIT_BURST_MULTIPLIER: int = 2
    
    # Security
    BCRYPT_ROUNDS: int = 12
    API_KEY_PREFIX: str = "ak_"
    API_KEY_LENGTH: int = 32
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Observability
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "agentshield"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4318"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @validator("APP_ENV")
    def validate_env(cls, v):
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"APP_ENV must be one of {valid_envs}")
        return v.lower()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()