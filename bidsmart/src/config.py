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

    # ── Matching ─────────────────────────────────────────────────────────
    semantic_match_threshold: float = 0.2       # cosine similarity floor for semantic matching

    # ── Image Recognition ──────────────────────────────────────────────────
    image_recognition_enabled: bool = True       # enable DeepSeek Vision for image OCR
    image_recognition_batch_size: int = 5        # images per concurrent batch
    image_recognition_timeout: int = 120          # total timeout seconds for all images

    # ── Compression Engine (100MB+ bid document tuning) ───────────────────
    compression_token_threshold: int = 40000      # L3 trigger threshold
    compression_tail_budget: int = 30000          # Tail message token budget
    compression_keep_recent: int = 5              # L1 preserve count
    compression_collapse_text_min: int = 5000     # L2 min text size
    compression_collapse_head: int = 1500         # L2 head chars
    compression_collapse_tail: int = 1000         # L2 tail chars
    compression_max_iterations: int = 30          # Agent loop limit
    compression_chunk_size: int = 2000            # Doc chunk tokens
    compression_chunk_overlap: int = 50           # Chunk overlap tokens
