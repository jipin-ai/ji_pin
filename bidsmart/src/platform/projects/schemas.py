"""Projects schemas — Pydantic models for request/response serialization."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Request schemas ─────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    """Schema for POST /projects."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    department: str | None = Field(None, max_length=255)
    editor: str | None = Field(None, max_length=255)
    bid_time: datetime | None = None


class ProjectUpdate(BaseModel):
    """Schema for PUT /projects/{id}. All fields optional — partial update."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    department: str | None = Field(None, max_length=255)
    editor: str | None = Field(None, max_length=255)
    bid_time: datetime | None = None


# ── Response schemas ────────────────────────────────────────────────────────

class ProjectResponse(BaseModel):
    """Schema for a single project response."""
    id: int
    name: str
    description: str | None
    department: str | None = None
    editor: str | None = None
    bid_time: datetime | None = None
    created_by: int
    document_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int
