"""Projects router — FastAPI endpoints for CRUD operations on projects."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.dependencies import get_current_user
from src.models.user import User
from src.platform.projects.schemas import (
    PaginatedResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from src.platform.projects.service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_response(project, doc_count: int = 0) -> ProjectResponse:
    """Convert ORM project to response schema."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        department=project.department,
        editor=project.editor,
        bid_time=project.bid_time,
        created_by=project.created_by,
        document_count=doc_count,
        created_at=project.created_at,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project with metadata (department, editor, bid_time)."""
    project = await project_service.create(db, data, current_user)
    return _project_to_response(project)


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List projects with RBAC filtering and pagination.

    Admin sees all projects; reviewer/viewer see only their own.
    """
    projects, total = await project_service.list_projects(db, current_user, page, page_size)

    items = []
    for p in projects:
        doc_count = await project_service._get_document_count(db, p.id)
        items.append(_project_to_response(p, doc_count))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single project by ID."""
    project = await project_service.get(db, project_id, current_user)
    doc_count = await project_service._get_document_count(db, project.id)
    return _project_to_response(project, doc_count)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a project. Owner or admin can update."""
    project = await project_service.update(db, project_id, data, current_user)
    return _project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project. Admin only. Cascade-deletes associated documents."""
    settings = request.app.state.settings
    await project_service.delete(db, project_id, current_user, settings=settings)
