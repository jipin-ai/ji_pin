"""Coordinator node configuration via Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Tongrui AI Secure Gateway"
    app_port: int = 8001
    debug: bool = False

    # Database — reuse existing PostgreSQL with table prefix isolation
    database_url: str = (
        "postgresql+asyncpg://mixing:mixing_dev@localhost:5432/mixing_console"
    )
    database_table_prefix: str = "tr_"  # tongrui namespace
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720  # 12 hours

    # mTLS
    ca_cert_path: str = "certs/ca.crt"
    ca_key_path: str = "certs/ca.key"
    server_cert_path: str = "certs/server.crt"
    server_key_path: str = "certs/server.key"

    # Node heartbeat
    heartbeat_interval_seconds: int = 30
    heartbeat_miss_threshold: int = 3

    # Audit
    audit_retention_days: int = 90


settings = Settings()
