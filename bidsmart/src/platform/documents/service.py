"""Document file service — upload, download, metadata."""

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.project import Project
from src.models.user import User
from src.storage.base import StorageBackend

# Allowed file extensions (lowercase, with dot)
ALLOWED_EXTENSIONS: set[str] = {".docx", ".pdf", ".wps", ".txt"}

# Mapping from extension → MIME type hints (used as fallback)
_MIME_MAP: dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".wps": "application/kswps",
    ".txt": "text/plain",
}


class FileService:
    """Stateless service for document upload, download, and metadata retrieval."""

    # ── Upload ──────────────────────────────────────────────────────────────

    async def upload(
        self,
        db: AsyncSession,
        project_id: int,
        file: UploadFile,
        user: User,
        storage: StorageBackend,
        max_size_bytes: int,
    ) -> Document:
        """Validate and persist an uploaded file.

        Returns the created Document ORM instance (pending flush).
        """
        # 1. Validate filename / extension
        original_name = file.filename or "unnamed"
        dot_pos = original_name.rfind(".")
        if dot_pos == -1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: no extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        extension = original_name[dot_pos:].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{extension}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        # 2. Verify project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        # 3. Read file content and validate size
        content = await file.read()
        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_size_bytes // (1024*1024)} MB",
            )

        # 4. Determine MIME type (use provided or fallback)
        mime_type = file.content_type or _MIME_MAP.get(extension, "application/octet-stream")

        # 5. Persist to storage
        storage_path = await storage.save(str(project_id), content, extension)

        # 6. Create DB record
        doc = Document(
            project_id=project_id,
            filename=storage_path.rsplit("/", 1)[-1],
            original_name=original_name,
            size=len(content),
            mime_type=mime_type,
            storage_path=storage_path,
            uploaded_by=user.id,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return doc

    # ── Download ────────────────────────────────────────────────────────────

    async def download(
        self,
        db: AsyncSession,
        document_id: int,
        storage: StorageBackend,
    ) -> tuple[bytes, str, str]:
        """Return (content, mime_type, original_name) for streaming.

        Raises 404 if the document does not exist.
        """
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        try:
            content = await storage.get(doc.storage_path)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document file missing from storage",
            )

        return content, doc.mime_type, doc.original_name

    # ── Metadata ────────────────────────────────────────────────────────────

    async def get_metadata(
        self,
        db: AsyncSession,
        document_id: int,
    ) -> Document:
        """Return the Document ORM record for the given id.

        Raises 404 if not found.
        """
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )
        return doc


# Module-level singleton
file_service = FileService()
