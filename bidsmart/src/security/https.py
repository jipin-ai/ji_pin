"""HTTPS enforcement middleware — redirect HTTP to HTTPS.

P1 feature — skeleton with TODO for full implementation.

Full implementation would:
1. Detect HTTP (non-TLS) requests
2. Issue 301/308 redirect to the HTTPS equivalent URL
3. Set HSTS header on HTTPS responses
4. Optionally allow specific paths over HTTP (e.g., health checks)
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send


class HTTPSRedirectMiddleware:
    """Redirect HTTP requests to HTTPS (P1 skeleton).

    TODO: Implement full HTTPS enforcement:
        - Check scope["scheme"] == "http"
        - Build redirect URL with HTTPS scheme
        - Return 301 Moved Permanently or 308 Permanent Redirect
        - Add Strict-Transport-Security header on HTTPS responses
        - Configurable exempt paths (e.g., /health)
    """

    def __init__(self, app: ASGIApp, enabled: bool = True) -> None:
        """Initialize the HTTPS redirect middleware.

        Args:
            app: The inner ASGI application.
            enabled: Whether HTTPS enforcement is active. Default True.
                     Currently ignored (skeleton).
        """
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass through (skeleton — HTTPS enforcement not yet implemented)."""
        if scope["type"] == "http":
            # TODO: Check if scheme is "http"
            # TODO: If enabled and scheme is http, redirect to https
            # TODO: On HTTPS responses, add HSTS header
            pass

        await self.app(scope, receive, send)
