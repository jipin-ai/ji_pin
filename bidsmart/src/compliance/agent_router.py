"""Agent Review Router — FastAPI endpoints for multi-turn compliance review.

POST /ai/review-agent        — Start a new agent review session
POST /ai/review-agent/continue — Continue an existing session
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.compliance.agent_loop import AgentReviewLoop

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Agent Review"])


# ── Request/Response Models ──────────────────────────────────────────────


class AgentReviewRequest(BaseModel):
    """Request to start or continue an agent review session."""

    project_id: int = Field(..., description="Project ID containing the bid document")
    message: str = Field(..., description="User's review request or follow-up question")
    session_id: Optional[str] = Field(None, description="Session ID to continue (omit for new session)")


class AgentReviewResponse(BaseModel):
    """Response from the agent review loop."""

    content: str = Field("", description="Agent's final text response")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    iterations: int = Field(0)
    session_id: str = Field("")
    compression_stats: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(None)


# ── In-memory agent store (per project) ──────────────────────────────────

_agents: Dict[int, AgentReviewLoop] = {}


async def _get_or_create_agent(project_id: int, settings) -> AgentReviewLoop:
    """Get or create an AgentReviewLoop for a project.

    In production, this would load document chunks from the database
    and initialize the embedder for knowledge base search.
    """
    if project_id in _agents:
        return _agents[project_id]

    agent = AgentReviewLoop(
        settings=settings,
        chunks=[],  # Chunks loaded lazily on first doc access
        max_iterations=getattr(settings, "compression_max_iterations", 30),
    )

    # Try to initialize knowledge base embedder
    try:
        from src.knowledge.embedder import get_embedder
        embedder = get_embedder()
        agent.set_embedder(embedder)
    except Exception as e:
        logger.warning(f"KB embedder init failed (search_kb will be unavailable): {e}")

    _agents[project_id] = agent
    return agent


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/review-agent", response_model=AgentReviewResponse)
async def review_agent(req: AgentReviewRequest):
    """Start a new agent review session for multi-turn compliance review."""
    from src.config import Settings as AppSettings

    app_settings = AppSettings()
    agent = await _get_or_create_agent(req.project_id, app_settings)
    result = await agent.run(user_message=req.message, session_id=req.session_id)
    return AgentReviewResponse(**result)


@router.post("/review-agent/continue", response_model=AgentReviewResponse)
async def review_agent_continue(req: AgentReviewRequest):
    """Continue an existing agent review session."""
    from src.config import Settings as AppSettings

    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id is required to continue")

    app_settings = AppSettings()
    agent = await _get_or_create_agent(req.project_id, app_settings)
    result = await agent.continue_session(session_id=req.session_id, user_message=req.message)
    return AgentReviewResponse(**result)


@router.get("/review-agent/sessions")
async def list_sessions():
    """List active agent review sessions."""
    from src.compliance.agent_loop import _sessions
    return {
        "count": len(_sessions),
        "sessions": [
            {
                "id": sid,
                "iteration_count": s["iteration_count"],
                "message_count": len(s["messages"]),
                "compression_stats": s["compression_stats"],
            }
            for sid, s in _sessions.items()
        ],
    }
