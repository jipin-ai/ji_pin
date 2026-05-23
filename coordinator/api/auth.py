"""POST /api/v1/auth/login — JWT token issuance."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from auth import create_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate user and return JWT.

    V1.0: accepts any non-empty credentials (dev mode).
    V1.5: replace with real user database lookup.
    """
    if not body.username or not body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_token(
        user_id=body.username,
        role="admin" if body.username == "admin" else "viewer",
    )
    return TokenResponse(access_token=token)
