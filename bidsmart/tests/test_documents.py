"""Tests for Documents module — upload, download, validation.

TDD: All tests written first (RED), then implementation makes them GREEN.
"""

import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.models.document import Document
from src.models.project import Project
from src.models.user import User
from src.platform.auth.service import auth_service


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _register_and_login(
    client: AsyncClient, username: str, password: str, role: str = "viewer"
) -> str:
    """Register a user, log in, and return the access_token."""
    await client.post(
        "/auth/register",
        json={"username": username, "password": password, "role": role},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    return login_resp.json()["access_token"]


async def _create_project(db_session, name: str = "test-project", created_by: int = 1) -> Project:
    """Create a project directly in the DB and return it."""
    project = Project(name=name, description="test", created_by=created_by)
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


def _make_upload_file(content: bytes, filename: str, content_type: str = "application/octet-stream"):
    """Return a tuple of (files_dict) suitable for httpx client.post."""
    return {"file": (filename, io.BytesIO(content), content_type)}


# ═══════════════════════════════════════════════════════════════════════════
# Upload Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUploadDocuments:
    """Task 5.3 / 5.4 — Document upload."""

    async def test_upload_docx_success(self, client: AsyncClient, db_session):
        """POST /projects/{id}/documents with .docx → 201 + DocumentResponse."""
        token = await _register_and_login(client, "uploader1", "pass1", role="reviewer")
        project = await _create_project(db_session, "proj-docx", created_by=1)

        docx_content = b"PK\x03\x04" + b"\x00" * 100  # minimal docx-like bytes
        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(docx_content, "bid.docx",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["original_name"] == "bid.docx"
        assert data["mime_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert data["size"] == len(docx_content)
        assert "id" in data
        assert "project_id" in data
        assert data["project_id"] == project.id
        assert "filename" in data
        assert "created_at" in data
        # Verify DB record exists
        result = await db_session.execute(select(Document).where(Document.id == data["id"]))
        doc = result.scalar_one_or_none()
        assert doc is not None
        assert doc.original_name == "bid.docx"

    async def test_upload_pdf_success(self, client: AsyncClient, db_session):
        """POST /projects/{id}/documents with .pdf → 201."""
        token = await _register_and_login(client, "uploader2", "pass2", role="reviewer")
        project = await _create_project(db_session, "proj-pdf", created_by=1)

        pdf_content = b"%PDF-1.4\n" + b"\x00" * 100
        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(pdf_content, "proposal.pdf", "application/pdf"),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["original_name"] == "proposal.pdf"
        assert data["mime_type"] == "application/pdf"

    async def test_upload_txt_success(self, client: AsyncClient, db_session):
        """POST /projects/{id}/documents with .txt → 201."""
        token = await _register_and_login(client, "uploader3", "pass3", role="reviewer")
        project = await _create_project(db_session, "proj-txt", created_by=1)

        txt_content = b"Hello, this is a test document.\n"
        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(txt_content, "notes.txt", "text/plain"),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["original_name"] == "notes.txt"
        assert data["mime_type"] == "text/plain"

    async def test_upload_wps_success(self, client: AsyncClient, db_session):
        """POST /projects/{id}/documents with .wps → 201."""
        token = await _register_and_login(client, "uploader3b", "pass3b", role="admin")
        project = await _create_project(db_session, "proj-wps", created_by=1)

        wps_content = b"\xd0\xcf\x11\xe0" + b"\x00" * 100  # OLE2 header
        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(wps_content, "document.wps", "application/kswps"),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["original_name"] == "document.wps"

    async def test_upload_invalid_format_jpg(self, client: AsyncClient, db_session):
        """Uploading .jpg → 400 (unsupported format)."""
        token = await _register_and_login(client, "uploader4", "pass4", role="reviewer")
        project = await _create_project(db_session, "proj-jpg", created_by=1)

        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(b"\xff\xd8\xff\xe0", "photo.jpg", "image/jpeg"),
        )
        assert resp.status_code == 400, resp.text
        assert "format" in resp.json()["detail"].lower() or "unsupported" in resp.json()["detail"].lower()

    async def test_upload_invalid_format_exe(self, client: AsyncClient, db_session):
        """Uploading .exe → 400 (unsupported format)."""
        token = await _register_and_login(client, "uploader5", "pass5", role="reviewer")
        project = await _create_project(db_session, "proj-exe", created_by=1)

        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(b"MZ\x90\x00", "virus.exe", "application/x-msdownload"),
        )
        assert resp.status_code == 400, resp.text

    async def test_upload_no_extension(self, client: AsyncClient, db_session):
        """Uploading file with no extension → 400 (unsupported format)."""
        token = await _register_and_login(client, "uploader5b", "pass5b", role="reviewer")
        project = await _create_project(db_session, "proj-noext", created_by=1)

        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(b"data", "README", "text/plain"),
        )
        assert resp.status_code == 400, resp.text

    async def test_upload_oversized(self, client: AsyncClient, db_session):
        """Uploading a file over the size limit → 413."""
        token = await _register_and_login(client, "uploader6", "pass6", role="reviewer")
        project = await _create_project(db_session, "proj-big", created_by=1)

        # Test settings have max_upload_size_mb=1, so >1MB should be rejected
        big_content = b"x" * (1 * 1024 * 1024 + 100)  # just over 1MB
        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(big_content, "big.docx",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        assert resp.status_code == 413, resp.text

    async def test_upload_requires_reviewer_role(self, client: AsyncClient, db_session):
        """Viewer trying to upload → 403 Forbidden."""
        token = await _register_and_login(client, "viewer1", "pass7", role="viewer")
        project = await _create_project(db_session, "proj-viewer", created_by=1)

        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(b"test", "doc.docx",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        assert resp.status_code == 403, resp.text

    async def test_upload_requires_auth(self, client: AsyncClient, db_session):
        """No auth header on upload → 401."""
        project = await _create_project(db_session, "proj-noauth", created_by=1)

        resp = await client.post(
            f"/projects/{project.id}/documents",
            files=_make_upload_file(b"test", "doc.docx",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        assert resp.status_code == 401, resp.text

    async def test_upload_project_not_found(self, client: AsyncClient):
        """Upload to non-existent project → 404."""
        token = await _register_and_login(client, "uploader7", "pass8", role="reviewer")

        resp = await client.post(
            "/projects/99999/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(b"test", "doc.docx",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        assert resp.status_code == 404, resp.text


# ═══════════════════════════════════════════════════════════════════════════
# Download Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDownloadDocuments:
    """Task 5.3 / 5.4 — Document download."""

    @pytest.fixture
    async def uploaded_doc(self, client: AsyncClient, db_session):
        """Upload a document and return its response data + token."""
        token = await _register_and_login(client, "downloader1", "pass9", role="reviewer")
        project = await _create_project(db_session, "proj-dl", created_by=1)

        content = b"Test download content.\n"
        resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(content, "download-test.txt", "text/plain"),
        )
        assert resp.status_code == 201
        return {"token": token, "doc": resp.json(), "content": content}

    async def test_download_success(self, client: AsyncClient, uploaded_doc):
        """GET /documents/{id}/download → 200 with correct Content-Type."""
        doc = uploaded_doc["doc"]
        token = uploaded_doc["token"]

        resp = await client.get(
            f"/documents/{doc['id']}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("content-type", "").startswith("text/plain")
        assert resp.content == uploaded_doc["content"]

    async def test_download_content_type_pdf(self, client: AsyncClient, db_session):
        """Download a PDF → Content-Type: application/pdf."""
        token = await _register_and_login(client, "dl-pdf", "pass10", role="reviewer")
        project = await _create_project(db_session, "proj-dlpdf", created_by=1)

        pdf_content = b"%PDF-test\n"
        upload_resp = await client.post(
            f"/projects/{project.id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=_make_upload_file(pdf_content, "test.pdf", "application/pdf"),
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.get(
            f"/documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")

    async def test_download_unauthorized(self, client: AsyncClient, uploaded_doc):
        """GET /documents/{id}/download without auth → 403."""
        doc = uploaded_doc["doc"]

        resp = await client.get(f"/documents/{doc['id']}/download")
        assert resp.status_code == 403, resp.text

    async def test_download_not_found(self, client: AsyncClient, uploaded_doc):
        """GET /documents/{id}/download for non-existent doc → 404."""
        token = uploaded_doc["token"]

        resp = await client.get(
            "/documents/99999/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text


# ═══════════════════════════════════════════════════════════════════════════
# Storage Backend Unit Tests (Task 5.1)
# ═══════════════════════════════════════════════════════════════════════════

class TestStorageBackend:
    """Task 5.1 — LocalFileStorage."""

    async def test_save_and_get(self, tmp_path):
        """Save a file, then retrieve it."""
        from src.storage.local import LocalFileStorage

        storage = LocalFileStorage(str(tmp_path))
        content = b"hello storage"
        path = await storage.save("project-1", content)

        assert path.startswith("project-1/")
        # File should exist on disk
        full_path = tmp_path / path
        assert full_path.exists()
        assert full_path.read_bytes() == content

    async def test_get_returns_bytes(self, tmp_path):
        """Get returns file content as bytes."""
        from src.storage.local import LocalFileStorage

        storage = LocalFileStorage(str(tmp_path))
        content = b"binary data"
        path = await storage.save("proj-a", content)

        result = await storage.get(path)
        assert result == content

    async def test_get_nonexistent_raises(self, tmp_path):
        """Get on nonexistent path raises FileNotFoundError."""
        from src.storage.local import LocalFileStorage

        storage = LocalFileStorage(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            await storage.get("nonexistent/file.bin")

    async def test_delete_removes_file(self, tmp_path):
        """Delete removes the file and its parent dirs if empty."""
        from src.storage.local import LocalFileStorage

        storage = LocalFileStorage(str(tmp_path))
        content = b"to be deleted"
        path = await storage.save("del-proj", content)

        await storage.delete(path)
        full_path = tmp_path / path
        assert not full_path.exists()

    async def test_save_creates_unique_names(self, tmp_path):
        """Two saves produce different filenames."""
        from src.storage.local import LocalFileStorage

        storage = LocalFileStorage(str(tmp_path))
        path1 = await storage.save("proj", b"aaa")
        path2 = await storage.save("proj", b"bbb")

        assert path1 != path2

    async def test_save_preserves_extension(self, tmp_path):
        """UUID filename preserves original extension."""
        from src.storage.local import LocalFileStorage

        storage = LocalFileStorage(str(tmp_path))
        path = await storage.save("proj-x", b"data", extension=".pdf")

        assert path.endswith(".pdf")
