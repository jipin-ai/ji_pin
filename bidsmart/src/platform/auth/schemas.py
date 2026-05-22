"""Auth schemas — Pydantic models for request/response serialization."""

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class RoleEnum(str, enum.Enum):
    """User role enumeration, matches UserRole in models."""
    admin = "admin"
    reviewer = "reviewer"
    viewer = "viewer"
    bid_editor = "bid_editor"


# ── Request schemas ─────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Schema for POST /auth/register."""
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    role: RoleEnum = RoleEnum.viewer


class LoginRequest(BaseModel):
    """Schema for POST /auth/login."""
    username: str
    password: str


class RefreshRequest(BaseModel):
    """Schema for POST /auth/refresh."""
    refresh_token: str


# ── Response schemas ────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Schema for token responses."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class UserResponse(BaseModel):
    """Schema for user data responses (never exposes password hash)."""
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
