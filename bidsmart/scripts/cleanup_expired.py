"""清理过期项目 — 投标日期已过的项目自动删除。

使用方式:
  python scripts/cleanup_expired.py          # 预览（dry-run）
  python scripts/cleanup_expired.py --commit  # 实际删除

通过 cron 每天执行:
  0 3 * * * cd /root/bidsmart && python scripts/cleanup_expired.py --commit >> logs/cleanup.log 2>&1
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cleanup")


async def cleanup_expired(commit: bool = False, max_projects: int = 50):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from src.config import Settings

    settings = Settings()
    engine = create_async_engine(
        settings.database_url.replace("sqlite+aiosqlite", "sqlite+aiosqlite"),
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys = ON"))

    async with AsyncSession(engine) as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            text("""
                SELECT id, name, bid_time FROM projects
                WHERE bid_time IS NOT NULL AND bid_time < :now
                ORDER BY bid_time ASC
                LIMIT :limit
            """),
            {"now": now.isoformat(), "limit": max_projects},
        )
        expired = result.fetchall()

        if not expired:
            logger.info("没有过期的项目需要清理")
            await engine.dispose()
            return

        logger.info(f"发现 {len(expired)} 个过期项目")

        deleted_count = 0
        for row in expired:
            proj_id, name, bid_time = row
            bid_str = str(bid_time)[:10]
            logger.info(f"{'[DRY-RUN]' if not commit else '[DELETE]'} #{proj_id}「{name}」投标日期: {bid_str}")

            if commit:
                # Delete files from storage
                doc_result = await db.execute(
                    text("SELECT storage_path FROM documents WHERE project_id = :pid"),
                    {"pid": proj_id},
                )
                docs = doc_result.fetchall()
                storage_root = Path(settings.storage_root)
                for (sp,) in docs:
                    fp = storage_root / sp
                    if fp.exists():
                        fp.unlink()
                        logger.info(f"  删除文件: {sp}")

                # Delete project (cascades: documents, review_sessions, project_members, confirmed_items, ignored_items)
                await db.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": proj_id})
                await db.commit()
                deleted_count += 1
                logger.info(f"  #{proj_id} 已删除")

        if commit:
            logger.info(f"完成: 删除 {deleted_count} 个项目")
        else:
            logger.info(f"[DRY-RUN] 将删除 {len(expired)} 个项目。加 --commit 执行。")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理过期投标项目")
    parser.add_argument("--commit", action="store_true", help="实际删除")
    parser.add_argument("--max", type=int, default=50, help="单次上限（默认50）")
    args = parser.parse_args()
    asyncio.run(cleanup_expired(commit=args.commit, max_projects=args.max))
