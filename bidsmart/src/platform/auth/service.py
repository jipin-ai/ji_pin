"""Authentication service — business logic for register, login, JWT handling."""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.user import User, UserRole
from src.platform.auth.schemas import LoginRequest, RegisterRequest, TokenResponse


class TokenPair(TokenResponse):
    """Alias — returned by login/refresh, same shape as TokenResponse."""
    pass


class AuthService:
    """Stateless service for authentication and token management."""

    # ── Password helpers ───────────────────────────────────────────────────

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    # ── Token helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _create_token(
        username: str,
        token_type: str,
        expires_delta: timedelta,
        settings: Settings,
    ) -> str:
        """Create a signed JWT with sub, type, and exp claims."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": username,
            "type": token_type,
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def _decode_token(token: str, settings: Settings) -> dict:
        """Decode and validate a JWT. Raises HTTPException on failure."""
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _create_token_pair(self, username: str, settings: Settings) -> TokenPair:
        """Generate both access and refresh tokens for a user."""
        access_expires = timedelta(minutes=settings.access_token_expire_minutes)
        refresh_expires = timedelta(minutes=settings.refresh_token_expire_minutes)

        access_token = self._create_token(username, "access", access_expires, settings)
        refresh_token = self._create_token(username, "refresh", refresh_expires, settings)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    # ── Service methods ────────────────────────────────────────────────────

    async def register(
        self, db: AsyncSession, data: RegisterRequest, settings: Settings,
    ) -> User:
        """Register a new user. Checks username uniqueness, hashes password."""
        # Check uniqueness
        result = await db.execute(select(User).where(User.username == data.username))
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )

        user = User(
            username=data.username,
            password_hash=self._hash_password(data.password),
            role=UserRole(data.role.value),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def login(
        self, db: AsyncSession, data: LoginRequest, settings: Settings,
    ) -> TokenPair:
        """Authenticate a user and return a token pair."""
        result = await db.execute(select(User).where(User.username == data.username))
        user = result.scalar_one_or_none()

        if user is None or not self._verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_pair = self._create_token_pair(user.username, settings)
        token_pair.must_change_password = user.must_change_password
        return token_pair

    async def refresh_token(
        self, db: AsyncSession, refresh_token: str, settings: Settings,
    ) -> TokenPair:
        """Validate a refresh token and issue a new token pair."""
        payload = self._decode_token(refresh_token, settings)

        # Verify token type is "refresh"
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not a refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user still exists
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._create_token_pair(username, settings)

    async def get_current_user(
        self, db: AsyncSession, token: str, settings: Settings,
    ) -> User:
        """Decode an access token and return the corresponding user."""
        payload = self._decode_token(token, settings)

        # Verify token type is "access"
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user



    async def change_password(
        self, db, user, new_password: str,
    ):
        user.password_hash = self._hash_password(new_password)
        user.must_change_password = False
        db.add(user)
        await db.flush()

# Module-level singleton — routers/dependencies grab this instance
auth_service = AuthService()
