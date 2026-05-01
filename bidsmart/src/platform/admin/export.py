"""Data export/import for server migration."""

import io
import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.dependencies import get_current_user, require_role
from src.models.user import User

router = APIRouter(prefix="/admin/data", tags=["admin-data"])


@router.post("/export")
async def export_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Export all data as tar.gz for migration."""
    import aiosqlite

    # Get DB path and storage path
    db_path = Path("bidsmart.db").resolve()
    storage_path = Path("storage").resolve()
    env_path = Path(".env").resolve()

    if not db_path.exists():
        raise HTTPException(500, "数据库文件不存在")

    # Create temp archive
    tmpdir = tempfile.mkdtemp(prefix="bidsmart_export_")
    try:
        # Copy DB (use VACUUM INTO for clean copy)
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(f"VACUUM INTO '{tmpdir}/bidsmart.db'")

        # Copy storage
        if storage_path.exists():
            shutil.copytree(storage_path, f"{tmpdir}/storage", symlinks=False, dirs_exist_ok=True)

        # Copy .env (redact API key)
        if env_path.exists():
            env_content = env_path.read_text()
            import re
            env_content = re.sub(r'(DEEPSEEK_API_KEY=)(\S+)', r'\1***REDACTED***', env_content)
            Path(f"{tmpdir}/.env").write_text(env_content)

        # Create tar.gz
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tar_path = f"{tmpdir}/bidsmart_export_{timestamp}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            for name in ["bidsmart.db", "storage", ".env"]:
                src = Path(f"{tmpdir}/{name}")
                if src.exists():
                    tar.add(src, arcname=name)

        # Stream the file
        tar_file = Path(tar_path)
        file_size = tar_file.stat().st_size

        def iterfile():
            with open(tar_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
            # Cleanup
            shutil.rmtree(tmpdir, ignore_errors=True)

        return StreamingResponse(
            iterfile(),
            media_type="application/gzip",
            headers={
                "Content-Disposition": f'attachment; filename="bidsmart_export_{timestamp}.tar.gz"',
                "Content-Length": str(file_size),
            },
        )
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(500, f"导出失败: {str(e)}")


@router.post("/import")
async def import_data(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Import data from a tar.gz export (merge mode)."""
    if not file.filename or not file.filename.endswith(".tar.gz"):
        raise HTTPException(400, "仅支持 .tar.gz 文件")

    tmpdir = tempfile.mkdtemp(prefix="bidsmart_import_")
    try:
        # Save upload
        tar_path = f"{tmpdir}/upload.tar.gz"
        content = await file.read()
        with open(tar_path, "wb") as f:
            f.write(content)

        # Extract
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(tmpdir)

        extracted = Path(tmpdir)

        # Validate
        if not (extracted / "bidsmart.db").exists():
            raise HTTPException(400, "无效的导出包：缺少 bidsmart.db")

        # Merge storage files
        storage_src = extracted / "storage"
        storage_dst = Path("storage").resolve()
        if storage_src.exists():
            storage_dst.mkdir(exist_ok=True)
            for f in storage_src.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(storage_src)
                    dst = storage_dst / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        shutil.copy2(f, dst)

        # Merge DB (append new records only — handled by caller via SQL)
        import aiosqlite
        async with aiosqlite.connect(str(extracted / "bidsmart.db")) as src_db:
            # Attach and merge users (skip existing usernames)
            await src_db.execute(f"ATTACH DATABASE '{Path('bidsmart.db').resolve()}' AS target")
            try:
                await src_db.execute("""
                    INSERT OR IGNORE INTO target.users SELECT * FROM main.users
                """)
                await src_db.execute("""
                    INSERT OR IGNORE INTO target.projects SELECT * FROM main.projects
                """)
                await src_db.execute("""
                    INSERT OR IGNORE INTO target.documents SELECT * FROM main.documents
                """)
                await src_db.execute("""
                    INSERT OR IGNORE INTO target.review_sessions SELECT * FROM main.review_sessions
                """)
                await src_db.execute("""
                    INSERT OR IGNORE INTO target.audit_logs SELECT * FROM main.audit_logs
                """)
            finally:
                await src_db.execute("DETACH DATABASE target")

        stats = {
            "storage_files": sum(1 for _ in storage_src.rglob("*")) if storage_src.exists() else 0,
            "message": "导入完成（合并模式）",
        }

        shutil.rmtree(tmpdir, ignore_errors=True)
        return stats
    except HTTPException:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(500, f"导入失败: {str(e)}")
