"""Node lifecycle — register, heartbeat, deregister."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_token, require_role
from cache import record_heartbeat, set_node_online, set_node_offline
from certs import issue_cert
from db.engine import get_db
from db.models import Node

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class RegisterRequest(BaseModel):
    name: str
    org_name: str


class RegisterResponse(BaseModel):
    node_id: str
    token: str  # registration token (JWT for the node)


@router.post("/register", response_model=RegisterResponse)
async def register_node(body: RegisterRequest, session: AsyncSession = Depends(get_db)):
    """Register a new gateway node. Returns node_id and registration token.

    V1.0: Certificate verification skipped (no mTLS in dev).
    V1.5: mTLS client certificate required.
    """
    # Generate cert
    cert_path, key_path = issue_cert(body.name)

    # Check name uniqueness
    result = await session.execute(select(Node).where(Node.name == body.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node name '{body.name}' already registered",
        )

    # Create node record
    node = Node(
        name=body.name,
        org_name=body.org_name,
        status="PENDING",
    )
    session.add(node)
    await session.commit()

    # Mark online in Redis
    await set_node_online(node.node_id)

    # Issue JWT for the node
    token = create_token(user_id=node.node_id, role="operator")

    return RegisterResponse(node_id=node.node_id, token=token)


class HeartbeatRequest(BaseModel):
    timestamp: str
    status: str
    load_avg: float = 0.0
    disk_usage: float = 0.0
    active_tasks: int = 0


@router.post("/{node_id}/heartbeat")
async def node_heartbeat(
    node_id: str, body: HeartbeatRequest, session: AsyncSession = Depends(get_db)
):
    """Receive heartbeat from a gateway node."""
    # Update Redis (fast path)
    await record_heartbeat(node_id, body.model_dump())
    await set_node_online(node_id)

    # Update PostgreSQL
    await session.execute(
        update(Node)
        .where(Node.node_id == node_id)
        .values(
            status="ONLINE",
            heartbeat_at=datetime.now(timezone.utc),
            ip_address=None,
        )
    )
    await session.commit()

    return {"status": "ok"}


@router.get("/{node_id}/tasks/pending")
async def get_pending_tasks(node_id: str):
    """Node polls this to get pending tasks. V2.0: replace with WebSocket push."""
    # V1.0: placeholder — tasks not implemented yet
    return {"tasks": []}


@router.delete("/{node_id}")
async def deregister_node(
    node_id: str,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "operator")),
):
    """Deregister a node. Only admin/operator can do this."""
    result = await session.execute(
        update(Node)
        .where(Node.node_id == node_id, Node.status != "SUSPENDED")
        .values(status="SUSPENDED")
    )
    await session.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )

    await set_node_offline(node_id)
    return {"status": "deregistered"}
