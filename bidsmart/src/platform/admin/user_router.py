"""Admin user management — CRUD + audit logging."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.dependencies import get_current_user, require_role
from src.models.user import User, UserRole
from src.models.audit_log import AuditLog, AuditResult

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: str = "viewer"


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role.value,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


@router.post("", status_code=201)
async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a new user (admin only)."""
    # Check duplicate
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(409, f"用户名 {data.username} 已存在")

    # Validate role
    try:
        role = UserRole(data.role)
    except ValueError:
        raise HTTPException(400, f"无效角色: {data.role}。有效值: admin, reviewer, viewer, bid_editor")

    from passlib.hash import bcrypt
    user = User(
        username=data.username,
        password_hash=bcrypt.hash(data.password),
        role=role,
        must_change_password=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db.add(AuditLog(
        user_id=current_user.id, action="user_created", resource_type="user",
        resource_id=str(user.id), details={"username": data.username, "role": data.role},
        ip_address="127.0.0.1", result=AuditResult.success
    ))
    await db.commit()

    return {"id": user.id, "username": user.username, "role": user.role.value}


@router.put("/{user_id}/password")
async def reset_password(
    user_id: int,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Reset a user's password (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    from passlib.hash import bcrypt
    user.password_hash = bcrypt.hash(data.password)
    await db.commit()

    db.add(AuditLog(
        user_id=current_user.id, action="password_reset", resource_type="user",
        resource_id=str(user_id), details={"target_user": user.username},
        ip_address="127.0.0.1", result=AuditResult.success
    ))
    await db.commit()

    return {"message": f"已重置 {user.username} 的密码"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Delete a user (admin only). Cannot delete self."""
    if user_id == current_user.id:
        raise HTTPException(400, "不能删除自己的账号")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    username = user.username
    await db.delete(user)
    await db.commit()

    db.add(AuditLog(
        user_id=current_user.id, action="user_deleted", resource_type="user",
        resource_id=str(user_id), details={"username": username},
        ip_address="127.0.0.1", result=AuditResult.success
    ))
    await db.commit()

    return {"message": f"已删除用户 {username}"}
