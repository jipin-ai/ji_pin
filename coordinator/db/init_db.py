"""Database initialization — creates all tr_* tables.

Used during dev instead of Alembic (shared DB with mixing-console
prevents clean alembic chain).
"""
import asyncio
import sys

from db.engine import engine, Base
import db.models  # noqa: F401 — register all models


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ All tr_* tables created")


if __name__ == "__main__":
    asyncio.run(init_db())
