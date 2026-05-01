"""Admin router — key rotation and other admin-only endpoints."""

from fastapi import APIRouter, Depends, Request, status

from src.dependencies import get_current_user, require_role
from src.models.user import User
from src.security.keys import KeyManager

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_key_manager(request: Request) -> KeyManager:
    """Dependency: get the KeyManager from app state."""
    app = request.app
    if hasattr(app.state, "key_manager"):
        return app.state.key_manager
    # Fallback: create a new one (should not happen in production)
    km = KeyManager()
    km.generate_dek()
    return km


@router.post("/keys/rotate", status_code=status.HTTP_200_OK)
async def rotate_keys(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    key_manager: KeyManager = Depends(_get_key_manager),
):
    """Rotate the Data Encryption Key (DEK).

    Generates a new DEK, increments the version, and returns the new version.
    Old DEKs are retained so files encrypted with previous versions can still
    be decrypted.

    Requires admin role.
    """
    _dek, new_version = key_manager.rotate()
    return {
        "status": "ok",
        "message": "Key rotation successful",
        "new_version": new_version,
    }
