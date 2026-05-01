"""Auth router — FastAPI endpoints for register, login, refresh, and user info."""

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.dependencies import get_current_user, require_role
from src.models.user import User
from src.platform.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.platform.auth.service import auth_service

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    settings = request.app.state.settings
    user = await auth_service.register(db, data, settings)
    return UserResponse.model_validate(user)


@router.post("/auth/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and receive access + refresh tokens."""
    settings = request.app.state.settings
    return await auth_service.login(db, data, settings)


@router.post("/auth/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    data: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a refresh token for a new token pair."""
    settings = request.app.state.settings
    return await auth_service.refresh_token(db, data.refresh_token, settings)


@router.get("/auth/me", status_code=200)
async def get_current_user_info(
    current_user=Depends(get_current_user),
):
    """Return current user info (id, username, role)."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value,
    }


@router.get("/users/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)



class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


@router.put("/auth/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await auth_service.change_password(db, current_user, data.new_password)
    await db.commit()
    return {"message": "password updated"}

@router.get("/users/me/admin", status_code=status.HTTP_200_OK)
async def get_me_admin(current_user: User = Depends(require_role("admin"))):
    """Admin-only endpoint — returns current user info."""
    return {"username": current_user.username, "role": current_user.role}
