"""Application settings loaded via pydantic-settings (supports .env override)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """BidSmart platform configuration.

    All fields can be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./bidsmart.db"
    # PostgreSQL (commented out for P0 dev convenience):
    # database_url: str = "postgresql+asyncpg://bidsmart:bidsmart@localhost:5432/bidsmart"

    # ── JWT / Auth ────────────────────────────────────────────────────────
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24          # 24 hours
    refresh_token_expire_minutes: int = 60 * 24 * 7     # 7 days

    # ── Storage ───────────────────────────────────────────────────────────
    storage_root: str = "./storage"
    max_upload_size_mb: int = 250

    # ── Rate Limiting ─────────────────────────────────────────────────────
    rate_limit_per_minute: int = 100
    rate_limit_window_seconds: int = 60

    # ── AI / DeepSeek ─────────────────────────────────────────────────────
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
