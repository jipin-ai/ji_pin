"""Pytest fixtures for BidSmart test suite."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.db.base import Base
from src.db.session import get_db
import src.models  # noqa: F401 — register models with Base.metadata


# ── Test settings ──────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
        access_token_expire_minutes=60 * 24,
        refresh_token_expire_minutes=60 * 24 * 7,
        storage_root="./test-storage",
        max_upload_size_mb=1,  # small limit for testing oversized uploads
    )


# ── Test engine (module-scoped, one per test module) ───────────────────────
@pytest.fixture(scope="module")
async def test_engine(test_settings: Settings):
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        future=True,
    )
    yield engine
    await engine.dispose()


# ── Ensure tables exist (module-scoped, once per module) ───────────────────
@pytest.fixture(scope="module", autouse=True)
async def _create_tables(test_engine):
    """Create all tables before tests and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Per-test DB session (rolls back after each test) ──────────────────────
@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated DB session that rolls back after each test."""
    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ── Async test client with app ─────────────────────────────────────────────
@pytest.fixture
async def client(test_settings: Settings, db_session) -> AsyncGenerator[AsyncClient, None]:
    """Async test client wired to FastAPI app with test DB override."""
    from src.main import create_app

    app_instance = create_app()
    app_instance.state.settings = test_settings

    async def override_get_db():
        yield db_session

    app_instance.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Auth header helper ─────────────────────────────────────────────────────
def auth_header(token: str) -> dict[str, str]:
    """Return Authorization header dict for the given Bearer token."""
    return {"Authorization": f"Bearer {token}"}


# ── Settings alias ─────────────────────────────────────────────────────────
@pytest.fixture
def settings(test_settings: Settings) -> Settings:
    return test_settings
