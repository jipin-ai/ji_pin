"""Document router — upload, download, list, and delete endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.dependencies import get_current_user, require_role
from src.models.document import Document
from src.models.project import Project
from src.models.user import User
from src.platform.documents.schemas import DocumentResponse
from src.platform.documents.service import file_service
from src.storage.local import LocalFileStorage

router = APIRouter()

# Separate bearer scheme for download (auto_error=False so we can return 403)
_download_bearer = HTTPBearer(auto_error=False)


def _get_storage(request: Request) -> LocalFileStorage:
    """Dependency: build LocalFileStorage from app settings."""
    settings = request.app.state.settings
    return LocalFileStorage(settings.storage_root)


def _get_max_size(request: Request) -> int:
    """Dependency: max upload size in bytes."""
    settings = request.app.state.settings
    return settings.max_upload_size_mb * 1024 * 1024


# ── Upload ────────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: int,
    request: Request,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("reviewer", "admin")),
    storage: LocalFileStorage = Depends(_get_storage),
    max_size: int = Depends(_get_max_size),
):
    """Upload a document to a project.

    Requires reviewer or admin role. Accepted formats: .docx, .pdf, .wps, .txt.
    Maximum file size is configured via ``max_upload_size_mb``.
    """
    doc = await file_service.upload(db, project_id, file, current_user, storage, max_size)
    return DocumentResponse.model_validate(doc)


# ── List documents by project ─────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/documents",
    response_model=List[DocumentResponse],
)
async def list_project_documents(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents in a project. Any authenticated user can list."""
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


# ── Download ──────────────────────────────────────────────────────────────

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    storage: LocalFileStorage = Depends(_get_storage),
    credentials: HTTPAuthorizationCredentials | None = Depends(_download_bearer),
):
    """Download a document by ID.

    Returns the raw file bytes with the correct Content-Type and
    ``Content-Disposition: attachment`` header.

    Requires authentication (any role). Returns 403 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required to download documents",
        )
    try:
        settings = request.app.state.settings
        await get_current_user(
            request=request,
            credentials=credentials,
            db=db,
        )
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required to download documents",
        )

    content, mime_type, original_name = await file_service.download(db, document_id, storage)

    return StreamingResponse(
        iter([content]),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{original_name}"',
        },
    )
