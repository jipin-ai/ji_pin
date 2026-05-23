"""Gateway node configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Node identity
    node_name: str = "node-dev-1"
    org_name: str = "Dev Org"

    # Coordinator
    coordinator_url: str = "http://localhost:8001"
    coordinator_token: str = ""

    # Heartbeat
    heartbeat_interval: int = 30

    # Sandbox
    sandbox_data_dir: str = "/tmp/tongrui-sandbox/data"
    sandbox_output_dir: str = "/tmp/tongrui-sandbox/output"
    sandbox_timeout: int = 300

    # SQLite
    sqlite_path: str = "data/node.db"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8002


settings = Settings()
