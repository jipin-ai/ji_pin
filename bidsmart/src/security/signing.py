"""API signature middleware — HMAC-SHA256 request signing.

P1 feature — skeleton with TODO for full implementation.

Full implementation would:
1. Require clients to sign requests with a shared secret
2. Include timestamp and nonce in the signature for anti-replay
3. Validate signatures on the server side
4. Reject requests with invalid signatures or expired timestamps

For now, this is a pass-through middleware.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send


class SignatureMiddleware:
    """HMAC-SHA256 request signing middleware (P1 skeleton).

    TODO: Implement full HMAC-SHA256 request signing with:
        - Shared secret per API client
        - Canonical request format (method + path + body + timestamp + nonce)
        - Signature header: X-Signature: t=..., v1=...
        - Anti-replay via timestamp window (±5 minutes) + nonce cache
        - Configurable required/optional per-route
    """

    def __init__(self, app: ASGIApp, required: bool = False) -> None:
        """Initialize the signature middleware.

        Args:
            app: The inner ASGI application.
            required: If True, all requests MUST have valid signatures.
                      Currently ignored (skeleton).
        """
        self.app = app
        self.required = required

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass through (skeleton — signature validation not yet implemented)."""
        if scope["type"] == "http":
            # TODO: Extract X-Signature header
            # TODO: Compute expected signature
            # TODO: Compare (constant-time)
            # TODO: Validate timestamp window
            # TODO: Check nonce cache for replay
            pass

        await self.app(scope, receive, send)
