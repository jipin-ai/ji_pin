"""Document schemas — Pydantic models for request/response serialization."""

from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Schema returned after document upload and in document listings."""

    id: int
    project_id: int
    filename: str
    original_name: str
    size: int
    mime_type: str
    uploaded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
