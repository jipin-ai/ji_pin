"""In-memory sliding window rate limiter per client IP.

Uses asyncio.Lock for thread safety. Returns 429 with Retry-After when
the per-minute limit is exceeded.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


class RateLimiterMiddleware:
    """Pure ASGI middleware that enforces rate limiting per client IP.

    Configuration is read from app.state.settings:
      - rate_limit_per_minute (int): max requests per window (default 100)
      - rate_limit_window_seconds (int): sliding window size (default 60)
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        # Per-IP list of request timestamps (UNIX epoch float)
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        client_ip = self._get_client_ip(request)
        settings = request.app.state.settings

        limit = settings.rate_limit_per_minute
        window = settings.rate_limit_window_seconds
        now = time.monotonic()

        async with self._lock:
            # Sliding window: discard timestamps older than 'window'
            timestamps = self._requests.get(client_ip, [])
            cutoff = now - window
            # Keep only timestamps within the window
            timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(timestamps) >= limit:
                # Rate limited — compute Retry-After from oldest timestamp
                oldest = timestamps[0]
                retry_after = max(1, int(window - (now - oldest)) + 1)
                self._requests[client_ip] = timestamps  # persist cleaned list

                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
                await response(scope, receive, send)
                return

            # Allow the request — record the timestamp
            timestamps.append(now)
            self._requests[client_ip] = timestamps

        await self.app(scope, receive, send)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request, respecting X-Forwarded-For header."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain a comma-separated chain; take the first
            return forwarded.split(",")[0].strip()
        # Fall back to the direct client host
        client = request.client
        if client:
            return client.host or "unknown"
        return "unknown"
