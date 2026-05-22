"""FastAPI application factory for the BidSmart platform."""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import Settings


# ── Configure structured JSON logging for access logs ────────────────────
class _JsonFormatter(logging.Formatter):
    """Format log records with extra fields as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "client_ip": getattr(record, "client_ip", None),
        }
        return json.dumps(base, default=str)


_access_handler = logging.StreamHandler()
_access_handler.setFormatter(_JsonFormatter())
_access_logger = logging.getLogger("bidsmart.access")
_access_logger.addHandler(_access_handler)
_access_logger.setLevel(logging.INFO)
# Prevent propagation to root logger to avoid duplicate output
_access_logger.propagate = False


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    settings = Settings()  # loads from env / .env automatically

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup / shutdown lifecycle."""
        # Startup: ensure review_memory table exists
        try:
            from src.compliance.router import _ensure_review_memory_table
            await _ensure_review_memory_table()
        except Exception:
            pass
        yield
        # Shutdown: close connections, etc.

    app = FastAPI(
        title="标书智审 BidSmart Agent",
        version="1.1.1",
        lifespan=lifespan,
    )

    # ── Middleware (order: rate_limiter → audit → logging → app) ──────────
    from src.platform.middleware.rate_limit import RateLimiterMiddleware
    from src.platform.middleware.logging import AccessLogMiddleware
    from src.security.audit import AuditMiddleware

    app.add_middleware(RateLimiterMiddleware)   # outermost
    app.add_middleware(AuditMiddleware)         # audit logging
    app.add_middleware(AccessLogMiddleware)     # inner access log

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": app.version}

    # ── Routers ────────────────────────────────────────────────────────────
    from src.platform.auth.router import router as auth_router
    from src.platform.projects.router import router as projects_router
    from src.platform.documents.router import router as documents_router
    from src.platform.admin.user_router import router as admin_user_router
    from src.platform.admin.export import router as admin_export_router
    from src.knowledge.router import router as knowledge_router
    from src.knowledge import models as kb_models

    app.include_router(auth_router, tags=["auth"])
    app.include_router(projects_router)
    app.include_router(documents_router, tags=["documents"])
    app.include_router(admin_user_router)
    app.include_router(admin_export_router)
    app.include_router(knowledge_router)

    # ── Admin (security) ──────────────────────────────────────────────────
    from fastapi import APIRouter, Depends
    from src.dependencies import get_current_user, require_role
    from src.security.keys import KeyManager

    admin_router = APIRouter(prefix="/admin", tags=["admin"])
    _key_mgr = KeyManager()

    @admin_router.post("/keys/rotate")
    async def rotate_keys(user=Depends(require_role("admin"))):
        _, new_version = _key_mgr.rotate()
        return {"message": "Keys rotated", "version": new_version}

    @admin_router.get("/keys/status")
    async def key_status(user=Depends(require_role("admin"))):
        return {"current_version": _key_mgr.current_version, "total_versions": len(_key_mgr._dek_store)}

    app.include_router(admin_router)

    # ── AI Compliance Review ──────────────────────────────────────────────
    from src.compliance.router import router as compliance_router
    from src.compliance.agent_router import router as agent_router
    app.include_router(compliance_router)
    app.include_router(agent_router)

    # ── Static Frontend ───────────────────────────────────────────────────
    from fastapi.staticfiles import StaticFiles
    import os as _os
    _static_dir = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "static")
    if _os.path.isdir(_static_dir):
        app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/")
    async def root():
        from fastapi.responses import FileResponse
        return FileResponse(_os.path.join(_static_dir, "index.html"))

    # Stash settings on the app state for downstream access
    app.state.settings = settings

    return app
