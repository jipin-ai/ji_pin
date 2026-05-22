"""Project service — business logic for CRUD operations with RBAC filtering."""

import os

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.project import Project
from src.models.user import User
from src.platform.projects.schemas import ProjectCreate, ProjectUpdate


class ProjectService:
    """Stateless service for project operations with RBAC enforcement."""

    # ── RBAC helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role.value == "admin"

    @staticmethod
    async def _get_or_404(db: AsyncSession, project_id: int) -> Project:
        """Fetch a project by id or raise 404."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    @staticmethod
    async def _check_ownership_or_admin(
        project: Project, user: User, action: str = "access",
    ) -> None:
        """Raise 403 unless user is admin or the project owner."""
        if not ProjectService._is_admin(user) and project.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to {action} this project",
            )

    @staticmethod
    async def _get_document_count(db: AsyncSession, project_id: int) -> int:
        """Count documents associated with a project."""
        result = await db.execute(
            select(func.count(Document.id)).where(Document.project_id == project_id)
        )
        return result.scalar() or 0

    # ── Service methods ────────────────────────────────────────────────────

    async def create(
        self, db: AsyncSession, data: ProjectCreate, user: User,
    ) -> Project:
        """Create a new project. Any authenticated user can create."""
        project = Project(
            name=data.name,
            description=data.description,
            department=data.department,
            editor=data.editor,
            bid_time=data.bid_time,
            created_by=user.id,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)
        return project

    async def list_projects(
        self, db: AsyncSession, user: User, page: int = 1, page_size: int = 20,
    ) -> tuple[list[Project], int]:
        """List projects with RBAC filtering and pagination.

        Admin sees all projects; reviewer/viewer see only their own.
        Returns (projects, total_count).
        """
        # Build base query
        query = select(Project)
        count_query = select(func.count(Project.id))

        if not self._is_admin(user):
            # Non-admin: filter by created_by
            query = query.where(Project.created_by == user.id)
            count_query = count_query.where(Project.created_by == user.id)

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)

        result = await db.execute(query)
        projects = list(result.scalars().all())

        return projects, total

    async def get(
        self, db: AsyncSession, project_id: int, user: User,
    ) -> Project:
        """Get a single project. Admin sees any; others only their own."""
        project = await self._get_or_404(db, project_id)
        await self._check_ownership_or_admin(project, user)
        return project

    async def update(
        self, db: AsyncSession, project_id: int, data: ProjectUpdate, user: User,
    ) -> Project:
        """Update a project. Owner or admin can update."""
        project = await self._get_or_404(db, project_id)
        await self._check_ownership_or_admin(project, user, action="update")

        # Apply partial updates
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.department is not None:
            project.department = data.department
        if data.editor is not None:
            project.editor = data.editor
        if data.bid_time is not None:
            project.bid_time = data.bid_time

        await db.flush()
        await db.refresh(project)
        return project

    async def delete(
        self, db: AsyncSession, project_id: int, user: User, settings=None,
    ) -> None:
        """Delete a project. Admin only. Cascade-deletes documents + storage files."""
        project = await self._get_or_404(db, project_id)

        if not self._is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete projects",
            )

        # Delete associated document files from storage
        result = await db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        documents = result.scalars().all()

        for doc in documents:
            # Try to remove the file from storage
            if settings is not None:
                full_path = os.path.join(settings.storage_root, doc.storage_path)
                try:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except OSError:
                    pass  # best-effort file deletion
            # Delete the document record
            await db.delete(doc)

        await db.flush()
        # Delete the project (cascade handles review_sessions and any remaining documents)
        await db.delete(project)
        await db.flush()


# Module-level singleton
project_service = ProjectService()
