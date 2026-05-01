"""Tests for Projects CRUD module — schemas, service, router, and RBAC filtering.

TDD: All tests written first (RED), then implementation makes them GREEN.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.project import Project


# ── Helpers ─────────────────────────────────────────────────────────────────

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


async def _token(client: AsyncClient, username: str, password: str, role: str = "viewer") -> str:
    """Register (if needed) and login, returning access_token."""
    await _register(client, username, password, role)
    resp = await _login(client, username, password)
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, token: str, name: str, description: str | None = None):
    return await client.post(
        "/projects",
        json={"name": name, "description": description},
        headers=_auth(token),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Create
# ═══════════════════════════════════════════════════════════════════════════

class TestProjectCreate:
    """Task 4.1 / 4.3 — POST /projects."""

    async def test_create_success(self, client: AsyncClient):
        """POST /projects → 201 with ProjectResponse."""
        token = await _token(client, "alice", "pass1")
        resp = await _create_project(client, token, "Bridge Tender", "A bridge project")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Bridge Tender"
        assert data["description"] == "A bridge project"
        assert "id" in data
        assert data["created_by"] is not None  # links to alice
        assert data["document_count"] == 0
        assert "created_at" in data

    async def test_create_minimal(self, client: AsyncClient):
        """POST /projects without description → 201."""
        token = await _token(client, "bob", "pass2")
        resp = await _create_project(client, token, "Road Tender")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Road Tender"
        assert data["description"] is None

    async def test_create_unauthorized(self, client: AsyncClient):
        """POST /projects without token → 401."""
        resp = await client.post("/projects", json={"name": "Nope"})
        assert resp.status_code == 401, resp.text


# ═══════════════════════════════════════════════════════════════════════════
#  List
# ═══════════════════════════════════════════════════════════════════════════

class TestProjectList:
    """Task 4.2 / 4.3 — GET /projects with RBAC filtering."""

    async def test_list_admin_sees_all(self, client: AsyncClient):
        """Admin lists projects → sees all projects regardless of creator."""
        admin_tok = await _token(client, "admin1", "pass", role="admin")
        viewer_tok = await _token(client, "viewer1", "pass", role="viewer")

        await _create_project(client, admin_tok, "Admin Project")
        await _create_project(client, viewer_tok, "Viewer Project")

        resp = await client.get("/projects", headers=_auth(admin_tok))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        names = {p["name"] for p in data["items"]}
        assert names == {"Admin Project", "Viewer Project"}

    async def test_list_viewer_sees_only_own(self, client: AsyncClient):
        """Viewer lists projects → sees only their own."""
        admin_tok = await _token(client, "admin2", "pass", role="admin")
        viewer_tok = await _token(client, "viewer2", "pass", role="viewer")

        await _create_project(client, admin_tok, "Admin P1")
        await _create_project(client, viewer_tok, "Viewer P1")

        resp = await client.get("/projects", headers=_auth(viewer_tok))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Viewer P1"

    async def test_list_pagination(self, client: AsyncClient):
        """GET /projects?page=1&page_size=2 → returns paginated results."""
        admin_tok = await _token(client, "admin3", "pass", role="admin")
        for i in range(5):
            await _create_project(client, admin_tok, f"Project {i}")

        # Page 1
        resp = await client.get("/projects?page=1&page_size=2", headers=_auth(admin_tok))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2

        # Page 3 (last page, 1 item)
        resp = await client.get("/projects?page=3&page_size=2", headers=_auth(admin_tok))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["page"] == 3
        assert len(data["items"]) == 1

    async def test_list_unauthorized(self, client: AsyncClient):
        """GET /projects without token → 401."""
        resp = await client.get("/projects")
        assert resp.status_code == 401, resp.text

    async def test_list_empty(self, client: AsyncClient):
        """GET /projects with no projects created → empty list."""
        token = await _token(client, "emptylist", "pass")
        resp = await client.get("/projects", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


# ═══════════════════════════════════════════════════════════════════════════
#  Get
# ═══════════════════════════════════════════════════════════════════════════

class TestProjectGet:
    """Task 4.2 / 4.3 — GET /projects/{id} with RBAC."""

    async def test_get_own_project(self, client: AsyncClient):
        """Viewer gets their own project → 200."""
        viewer_tok = await _token(client, "getter", "pass")
        create_resp = await _create_project(client, viewer_tok, "My Project")
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/projects/{project_id}", headers=_auth(viewer_tok))
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "My Project"

    async def test_get_admin_sees_any(self, client: AsyncClient):
        """Admin gets another user's project → 200."""
        viewer_tok = await _token(client, "getviewer", "pass")
        admin_tok = await _token(client, "getadmin", "pass", role="admin")

        create_resp = await _create_project(client, viewer_tok, "Viewer's Project")
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/projects/{project_id}", headers=_auth(admin_tok))
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Viewer's Project"

    async def test_get_viewer_cannot_see_others(self, client: AsyncClient):
        """Viewer tries to get another user's project → 403."""
        alice_tok = await _token(client, "alice_get", "pass")
        bob_tok = await _token(client, "bob_get", "pass")

        create_resp = await _create_project(client, alice_tok, "Alice Project")
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/projects/{project_id}", headers=_auth(bob_tok))
        assert resp.status_code == 403, resp.text

    async def test_get_not_found(self, client: AsyncClient):
        """GET /projects/99999 → 404."""
        token = await _token(client, "nf_user", "pass")
        resp = await client.get("/projects/99999", headers=_auth(token))
        assert resp.status_code == 404, resp.text

    async def test_get_unauthorized(self, client: AsyncClient):
        """GET /projects/{id} without token → 401."""
        resp = await client.get("/projects/1")
        assert resp.status_code == 401, resp.text


# ═══════════════════════════════════════════════════════════════════════════
#  Update
# ═══════════════════════════════════════════════════════════════════════════

class TestProjectUpdate:
    """Task 4.2 / 4.3 — PUT /projects/{id}."""

    async def test_update_own_project(self, client: AsyncClient):
        """Owner updates their own project → 200."""
        token = await _token(client, "updater", "pass")
        create_resp = await _create_project(client, token, "Old Name", "Old Desc")
        project_id = create_resp.json()["id"]

        resp = await client.put(
            f"/projects/{project_id}",
            json={"name": "New Name", "description": "New Desc"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New Desc"

    async def test_update_partial(self, client: AsyncClient):
        """PUT with only name → only name changes, description unchanged."""
        token = await _token(client, "partial", "pass")
        create_resp = await _create_project(client, token, "Original", "Keep me")
        project_id = create_resp.json()["id"]

        resp = await client.put(
            f"/projects/{project_id}",
            json={"name": "Renamed"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Renamed"
        assert data["description"] == "Keep me"

    async def test_update_admin_can_update_any(self, client: AsyncClient):
        """Admin can update another user's project → 200."""
        viewer_tok = await _token(client, "up_viewer", "pass")
        admin_tok = await _token(client, "up_admin", "pass", role="admin")

        create_resp = await _create_project(client, viewer_tok, "Viewer's")
        project_id = create_resp.json()["id"]

        resp = await client.put(
            f"/projects/{project_id}",
            json={"name": "Admin Edits"},
            headers=_auth(admin_tok),
        )
        assert resp.status_code == 200, resp.text

    async def test_update_viewer_cannot_update_others(self, client: AsyncClient):
        """Viewer tries to update another user's project → 403."""
        alice_tok = await _token(client, "alice_up", "pass")
        bob_tok = await _token(client, "bob_up", "pass")

        create_resp = await _create_project(client, alice_tok, "Alice's")
        project_id = create_resp.json()["id"]

        resp = await client.put(
            f"/projects/{project_id}",
            json={"name": "Hijack"},
            headers=_auth(bob_tok),
        )
        assert resp.status_code == 403, resp.text

    async def test_update_not_found(self, client: AsyncClient):
        """PUT /projects/99999 → 404."""
        token = await _token(client, "nf_up", "pass")
        resp = await client.put(
            "/projects/99999",
            json={"name": "Ghost"},
            headers=_auth(token),
        )
        assert resp.status_code == 404, resp.text

    async def test_update_unauthorized(self, client: AsyncClient):
        """PUT /projects/{id} without token → 401."""
        resp = await client.put("/projects/1", json={"name": "Nope"})
        assert resp.status_code == 401, resp.text


# ═══════════════════════════════════════════════════════════════════════════
#  Delete
# ═══════════════════════════════════════════════════════════════════════════

class TestProjectDelete:
    """Task 4.2 / 4.3 — DELETE /projects/{id} with cascade."""

    async def test_delete_admin_success(self, client: AsyncClient):
        """Admin deletes a project → 204, project is gone."""
        admin_tok = await _token(client, "del_admin", "pass", role="admin")
        create_resp = await _create_project(client, admin_tok, "To Delete")
        project_id = create_resp.json()["id"]

        resp = await client.delete(f"/projects/{project_id}", headers=_auth(admin_tok))
        assert resp.status_code == 204, resp.text

        # Verify it's gone
        get_resp = await client.get(f"/projects/{project_id}", headers=_auth(admin_tok))
        assert get_resp.status_code == 404

    async def test_delete_viewer_cannot_delete(self, client: AsyncClient):
        """Viewer tries to delete any project → 403."""
        admin_tok = await _token(client, "del_admin2", "pass", role="admin")
        viewer_tok = await _token(client, "del_viewer", "pass", role="viewer")

        create_resp = await _create_project(client, viewer_tok, "My Project")
        project_id = create_resp.json()["id"]

        resp = await client.delete(f"/projects/{project_id}", headers=_auth(viewer_tok))
        assert resp.status_code == 403, resp.text

    async def test_delete_cascade_documents(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """Deleting a project cascades to associated documents."""
        admin_tok = await _token(client, "del_cascade", "pass", role="admin")

        # Create project via API
        create_resp = await _create_project(client, admin_tok, "Cascade Test")
        project_id = create_resp.json()["id"]

        # Manually insert a document linked to this project
        doc = Document(
            project_id=project_id,
            filename="test.pdf",
            original_name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            storage_path="/tmp/test.pdf",
            uploaded_by=1,  # the admin user
        )
        db_session.add(doc)
        await db_session.flush()
        doc_id = doc.id

        # Verify document exists
        result = await db_session.execute(
            select(Document).where(Document.id == doc_id)
        )
        assert result.scalar_one_or_none() is not None

        # Delete project via API
        resp = await client.delete(f"/projects/{project_id}", headers=_auth(admin_tok))
        assert resp.status_code == 204, resp.text

        # Verify document is cascade-deleted
        result = await db_session.execute(
            select(Document).where(Document.id == doc_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_not_found(self, client: AsyncClient):
        """DELETE /projects/99999 → 404."""
        admin_tok = await _token(client, "del_nf", "pass", role="admin")
        resp = await client.delete("/projects/99999", headers=_auth(admin_tok))
        assert resp.status_code == 404, resp.text

    async def test_delete_unauthorized(self, client: AsyncClient):
        """DELETE /projects/{id} without token → 401."""
        resp = await client.delete("/projects/1")
        assert resp.status_code == 401, resp.text
