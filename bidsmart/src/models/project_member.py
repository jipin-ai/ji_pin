"""ProjectMember model — tracks which users have access to which projects."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class ProjectMemberRole(str, enum.Enum):
    """Roles within a project."""
    owner = "owner"      # Full control: manage members, delete project
    editor = "editor"    # Upload documents, start reviews
    viewer = "viewer"    # Read-only access to project and its documents


class ProjectMember(Base):
    """Association between users and projects with a role.

    A user can have different roles in different projects.
    """

    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(ProjectMemberRole, name="project_member_role"),
        default=ProjectMemberRole.viewer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship("Project", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<ProjectMember project_id={self.project_id} "
            f"user_id={self.user_id} role={self.role.value}>"
        )
