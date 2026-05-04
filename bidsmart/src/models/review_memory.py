"""Review memory model — cross-project ignore/long-term memory."""

import hashlib
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ReviewMemory(Base):
    """Stores ignored review conclusions for cross-project reuse."""

    __tablename__ = "review_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_hash = Column(String(64), nullable=False, unique=True)
    requirement_preview = Column(String(200), nullable=False)
    verdict = Column(String(30), nullable=False)
    reason = Column(Text, default="")
    suggestion = Column(Text, default="")
    ignored_at = Column(DateTime, default=datetime.utcnow)
    ignore_count = Column(Integer, default=1)
    project_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_req_hash", "requirement_hash"),
    )

    @staticmethod
    def hash_requirement(text: str) -> str:
        """SHA256 hash of normalized requirement text."""
        # Normalize: trim, lowercase, remove extra whitespace
        normalized = " ".join(text.strip().lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()
