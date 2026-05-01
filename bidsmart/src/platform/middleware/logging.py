"""Pure ASGI access logging middleware — structured, fire-and-forget.

Logs method, path, status_code, duration_ms, and client_ip for every
HTTP request. Uses the standard logging module with structured extra fields.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Dedicated logger for access logs
access_logger = logging.getLogger("bidsmart.access")


class AccessLogMiddleware:
    """ASGI middleware that logs each HTTP request in structured JSON format.

    The log is emitted after the response status is determined, before the
    response body is sent to the client.  This is effectively fire-and-forget
    as logging is non-blocking.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = time.monotonic()
        status_code: int = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.monotonic() - start_time) * 1000)
            client_ip = self._get_client_ip(request)

            access_logger.info(
                "",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )

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
