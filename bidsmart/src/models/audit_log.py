"""AuditLog model — immutable audit trail for security-relevant events."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

# Use JSON type that works with SQLite and PostgreSQL
try:
    from sqlalchemy import JSON
except ImportError:
    from sqlalchemy.types import JSON


class AuditResult(str, enum.Enum):
    """Outcome of an audited action."""
    success = "success"
    failure = "failure"
    info = "info"


class AuditLog(Base):
    """Immutable audit trail recording who did what, when, from where, and the result.

    Audit logs are append-only — they should never be updated or deleted
    by application code.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Who performed the action (nullable for anonymous/system actions)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What action was performed (e.g., "document.upload", "user.login")
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # What resource was acted upon
    resource_type: Mapped[str] = mapped_column(
        String(127), nullable=False, index=True,
    )
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Additional structured details (JSON)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Where the request came from
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)

    # What happened
    result: Mapped[AuditResult] = mapped_column(
        Enum(AuditResult, name="audit_result"),
        default=AuditResult.info,
        nullable=False,
    )

    # When it happened (no updated_at — audit logs are immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action='{self.action}' "
            f"resource='{self.resource_type}:{self.resource_id}' "
            f"result={self.result.value}>"
        )
