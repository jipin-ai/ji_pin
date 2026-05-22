"""Tests for Auth module — schemas, service, router, and dependencies.

TDD: All tests written first (RED), then implementation makes them GREEN.
"""

import pytest
from httpx import AsyncClient

# We'll use the fixtures from conftest.py:
#   client       — AsyncClient for the FastAPI app (with test DB override)
#   settings     — test Settings with jwt_secret etc.
#   auth_header  — utility to build Authorization dict


# ── Helper: register a user and return the response ─────────────────────────
async def _register(client: AsyncClient, username: str, password: str, role: str = "viewer"):
    return await client.post(
        "/auth/register",
        json={"username": username, "password": password, "role": role},
    )


async def _login(client: AsyncClient, username: str, password: str):
    return await client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3.1  Auth Schemas (implicitly tested through API endpoints)
# ═══════════════════════════════════════════════════════════════════════════

class TestRegister:
    """Task 3.1 / 3.3 — Registration."""

    async def test_register_success(self, client: AsyncClient):
        """POST /auth/register → 201 with UserResponse."""
        resp = await _register(client, "alice", "secret123")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "alice"
        assert data["role"] == "viewer"
        assert "id" in data
        assert "created_at" in data
        # Password hash must NOT leak
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_duplicate_username(self, client: AsyncClient):
        """Second registration with same username → 409 Conflict."""
        await _register(client, "bob", "pass1")
        resp = await _register(client, "bob", "pass2")
        assert resp.status_code == 409, resp.text

    async def test_register_custom_role(self, client: AsyncClient):
        """Register with explicit role=reviewer."""
        resp = await _register(client, "carol", "pass3", role="reviewer")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["role"] == "reviewer"


class TestLogin:
    """Task 3.2 / 3.3 — Login."""

    async def test_login_success(self, client: AsyncClient):
        """POST /auth/login → 200 with TokenResponse."""
        await _register(client, "dave", "pass4")
        resp = await _login(client, "dave", "pass4")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Login with wrong password → 401."""
        await _register(client, "eve", "correct")
        resp = await _login(client, "eve", "wrong")
        assert resp.status_code == 401, resp.text

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login for unknown user → 401."""
        resp = await _login(client, "ghost", "nope")
        assert resp.status_code == 401, resp.text


class TestRefresh:
    """Task 3.2 / 3.3 — Token refresh."""

    async def test_refresh_token_success(self, client: AsyncClient):
        """POST /auth/refresh with valid refresh_token → 200 with new tokens."""
        await _register(client, "frank", "pass5")
        login_resp = await _login(client, "frank", "pass5")
        tokens = login_resp.json()

        refresh_resp = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_resp.status_code == 200, refresh_resp.text
        data = refresh_resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # Tokens should be new (different from originals — at least access_token)
        assert data["access_token"]  # verify new access token exists
        assert data["token_type"] == "bearer"

    async def test_refresh_with_access_token_rejected(self, client: AsyncClient):
        """Passing an access_token to /auth/refresh → 401 (type mismatch)."""
        await _register(client, "grace", "pass6")
        login_resp = await _login(client, "grace", "pass6")
        tokens = login_resp.json()

        resp = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["access_token"]},  # wrong token type
        )
        assert resp.status_code == 401, resp.text

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Garbage refresh_token → 401."""
        resp = await client.post(
            "/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert resp.status_code == 401, resp.text


class TestMeEndpoint:
    """Task 3.3 / 3.4 — GET /users/me."""

    async def test_me_endpoint(self, client: AsyncClient):
        """GET /users/me with valid Bearer token → 200 UserResponse."""
        await _register(client, "heidi", "pass7")
        login_resp = await _login(client, "heidi", "pass7")
        access_token = login_resp.json()["access_token"]

        me_resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200, me_resp.text
        data = me_resp.json()
        assert data["username"] == "heidi"
        assert data["role"] == "viewer"
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data

    async def test_me_unauthorized(self, client: AsyncClient):
        """GET /users/me without token → 401."""
        resp = await client.get("/users/me")
        assert resp.status_code == 401, resp.text

    async def test_me_invalid_token(self, client: AsyncClient):
        """GET /users/me with bogus token → 401."""
        resp = await client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401, resp.text

    async def test_me_wrong_scheme(self, client: AsyncClient):
        """GET /users/me with Basic auth → 401."""
        await _register(client, "ivan", "pass8")
        login_resp = await _login(client, "ivan", "pass8")
        access_token = login_resp.json()["access_token"]

        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Basic {access_token}"},
        )
        assert resp.status_code == 401, resp.text


class TestRolePermission:
    """Task 3.4 — Role-based access control (require_role)."""

    async def test_role_permission_viewer_restricted(self, client: AsyncClient):
        """A viewer hitting an admin-only endpoint → 403."""
        # Register as viewer (default)
        await _register(client, "judy", "pass9")
        login_resp = await _login(client, "judy", "pass9")
        access_token = login_resp.json()["access_token"]

        # Hit a protected endpoint that requires admin role
        resp = await client.get(
            "/users/me/admin",  # hypothetical admin-only endpoint
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # This endpoint may not exist yet — the test will fail RED
        # until we wire it in router + dependencies.  That's by design.
        assert resp.status_code == 403, resp.text

    async def test_role_permission_admin_access(self, client: AsyncClient):
        """An admin hitting an admin-only endpoint → 200."""
        # Register as admin
        await _register(client, "karen", "pass10", role="admin")
        login_resp = await _login(client, "karen", "pass10")
        access_token = login_resp.json()["access_token"]

        resp = await client.get(
            "/users/me/admin",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200, resp.text
