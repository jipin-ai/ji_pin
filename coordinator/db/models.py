"""Core database models for Tongrui AI Security Gateway.

All tables are prefixed with 'tr_' to coexist with other applications
sharing the same PostgreSQL database.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.engine import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Node(Base):
    """Gateway node registered with the coordinator."""

    __tablename__ = "tr_nodes"

    node_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING | ONLINE | OFFLINE | SUSPENDED
    ip_address: Mapped[str | None] = mapped_column(String(45))
    exposure_level: Mapped[str] = mapped_column(
        String(2), default="L0", nullable=False
    )  # L0 | L1 | L2
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=3)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Task(Base):
    """Analysis task created by a user."""

    __tablename__ = "tr_tasks"

    task_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workflow: Mapped[str] = mapped_column(
        String(20), default="PARALLEL", nullable=False
    )  # PARALLEL | SEQUENTIAL
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    required_exposure_level: Mapped[str] = mapped_column(
        String(2), default="L0", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING → ... → COMPLETED | PARTIAL | FAILED | CANCELLED
    script_id: Mapped[str | None] = mapped_column(String(64))
    aggregator_script_id: Mapped[str | None] = mapped_column(String(64))
    completeness_score: Mapped[int | None] = mapped_column(Integer)
    aggregate_result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list["TaskStep"]] = relationship(
        "TaskStep", back_populates="task", cascade="all, delete-orphan"
    )


class TaskStep(Base):
    """Per-node execution step within a task."""

    __tablename__ = "tr_task_steps"

    step_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tr_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tr_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
    )
    script_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(20), default="QUEUED", nullable=False
    )  # QUEUED | RUNNING | COMPLETED | FAILED | TIMEOUT
    result: Mapped[dict | None] = mapped_column(JSONB)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    sanitization_log: Mapped[list | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped["Task"] = relationship("Task", back_populates="steps")


class AuditLog(Base):
    """Immutable audit trail with HMAC integrity protection."""

    __tablename__ = "tr_audit_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    actor_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # USER | NODE | SYSTEM
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    hmac_signature: Mapped[str | None] = mapped_column(String(64))
