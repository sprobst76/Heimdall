"""Shared fixtures for Heimdall backend tests.

Uses SQLite (aiosqlite) by default — no PostgreSQL required.
Set TEST_DATABASE_URL to override (e.g. for CI with real PostgreSQL).
"""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite://")

# Ensure settings can be loaded without .env
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")

from app.database import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Engine — SQLite in-memory with StaticPool (shared across connections)
# ---------------------------------------------------------------------------

_engine_kwargs = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    _engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }

_engine = create_async_engine(TEST_DATABASE_URL, echo=False, **_engine_kwargs)
_TestSession = async_sessionmaker(
    bind=_engine, class_=AsyncSession, expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Session-scoped: create / drop tables
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_tables():
    import app.models  # noqa: F401 — populate Base.metadata

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


# ---------------------------------------------------------------------------
# Per-test session with rollback
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db_session():
    async with _TestSession() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    from app.database import get_db
    from app.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Convenience: registered parent with tokens + family_id
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def registered_parent(client: AsyncClient, db_session: AsyncSession):
    """Register a parent and return context dict.

    Keys: headers, user_id, family_id, email, tokens
    """
    from app.core.security import decode_token
    from app.models.user import User

    email = f"parent-{uuid.uuid4().hex[:8]}@test.de"
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "testpassword123",
        "name": "Test Eltern",
        "family_name": "Test Familie",
    })
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    payload = decode_token(tokens["access_token"])
    user_id = uuid.UUID(payload["sub"])

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    return {
        "headers": headers,
        "user_id": str(user.id),
        "family_id": str(user.family_id),
        "email": email,
        "tokens": tokens,
    }
