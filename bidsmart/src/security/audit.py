"""AuditMiddleware — async, non-blocking audit logging for every HTTP request.

Records who, what, when, ip, and result for every API call. Uses a background
task queue pattern to avoid blocking the response. Falls back to synchronous
logging if the database is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

audit_logger = logging.getLogger("bidsmart.audit")


class AuditMiddleware:
    """ASGI middleware that records an audit log for every HTTP request.

    Audit events are recorded asynchronously (fire-and-forget) so that
    the response is never delayed by audit logging.

    The audit record includes:
        - user_id: extracted from the authenticated user (if available)
        - action: "http.request"
        - resource_type: "http"
        - resource_id: f"{method}:{path}"
        - details: JSON with method, path, query_string, status_code, duration_ms
        - ip_address: client IP
        - result: "success" (2xx-3xx) or "failure" (4xx-5xx)
    """

    def __init__(
        self,
        app: ASGIApp,
        db_session_factory: Callable | None = None,
    ) -> None:
        """Initialize the audit middleware.

        Args:
            app: The inner ASGI application.
            db_session_factory: Optional async callable that returns an async DB
                                session. If None, audit events are logged only
                                (not persisted to DB).
        """
        self.app = app
        self._db_factory = db_session_factory
        self._audit_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._worker_task: asyncio.Task | None = None
        self._running = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = time.monotonic()
        status_code: int = 0

        # Start the background worker if not already running
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_audit_queue())

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.monotonic() - start_time) * 1000)

            # Build audit record
            audit_record = self._build_audit_record(request, status_code, duration_ms)

            # Fire-and-forget: put on queue for background processing
            try:
                self._audit_queue.put_nowait(audit_record)
            except asyncio.QueueFull:
                # Queue full — log at warning level and drop
                audit_logger.warning(
                    "Audit queue full, dropping record: %s %s -> %d",
                    request.method, request.url.path, status_code,
                )

            # Also log to structured audit logger immediately (non-blocking)
            audit_logger.info(
                "AUDIT",
                extra={
                    "action": audit_record["action"],
                    "method": audit_record.get("method", ""),
                    "path": audit_record.get("path", ""),
                    "status_code": audit_record.get("status_code", 0),
                    "duration_ms": duration_ms,
                    "client_ip": audit_record.get("ip_address", ""),
                    "user_id": audit_record.get("user_id"),
                    "result": audit_record.get("result", ""),
                },
            )

    # ── Background worker ───────────────────────────────────────────────────

    async def _process_audit_queue(self) -> None:
        """Background worker that drains the audit queue and persists to DB."""
        while self._running:
            try:
                # Batch drain: get up to 50 records at a time
                batch: list[dict[str, Any]] = []
                try:
                    # Get first record (blocking with timeout)
                    record = await asyncio.wait_for(self._audit_queue.get(), timeout=1.0)
                    batch.append(record)
                except asyncio.TimeoutError:
                    continue

                # Drain remaining records without blocking
                while len(batch) < 50:
                    try:
                        record = self._audit_queue.get_nowait()
                        batch.append(record)
                    except asyncio.QueueEmpty:
                        break

                # Persist batch to DB if factory is available
                if self._db_factory is not None and batch:
                    await self._persist_batch(batch)

            except Exception:
                audit_logger.exception("Error processing audit queue")

    async def _persist_batch(self, batch: list[dict[str, Any]]) -> None:
        """Persist a batch of audit records to the database."""
        try:
            from src.models.audit_log import AuditLog

            async for session in self._db_factory():
                try:
                    for record in batch:
                        log = AuditLog(
                            user_id=record.get("user_id"),
                            action=record.get("action", "http.request"),
                            resource_type=record.get("resource_type", "http"),
                            resource_id=record.get("resource_id", ""),
                            details=record.get("details", {}),
                            ip_address=record.get("ip_address", ""),
                            result=record.get("result", "success"),
                        )
                        session.add(log)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    break  # Only need one session from the generator
        except Exception:
            audit_logger.exception("Failed to persist audit batch to DB")

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _build_audit_record(
        self, request: Request, status_code: int, duration_ms: float
    ) -> dict[str, Any]:
        """Build an audit record dictionary from request/response data."""
        client_ip = self._get_client_ip(request)
        result = "success" if 200 <= status_code < 400 else "failure"

        # Try to extract user_id from request state (set by auth middleware)
        user_id = None
        if hasattr(request, "state") and hasattr(request.state, "user_id"):
            user_id = request.state.user_id

        return {
            "user_id": user_id,
            "action": "http.request",
            "resource_type": "http",
            "resource_id": f"{request.method}:{request.url.path}",
            "details": {
                "method": request.method,
                "path": request.url.path,
                "query_string": str(request.url.query) if request.url.query else "",
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
            "ip_address": client_ip,
            "result": result,
        }

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request, respecting X-Forwarded-For header."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        if client:
            return client.host or "unknown"
        return "unknown"

    # ── Cleanup ─────────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Gracefully shut down the background audit worker."""
        self._running = False
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
