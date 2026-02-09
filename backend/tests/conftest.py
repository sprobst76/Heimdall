"""Shared fixtures for Heimdall backend tests.

Integration tests require PostgreSQL. Set TEST_DATABASE_URL env var or
use the default: postgresql+asyncpg://heimdall:heimdall@localhost:5432/heimdall_test

If PostgreSQL is unreachable, integration tests are automatically skipped.
Unit tests (test_unit_*.py) always run without a database.
"""

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# PostgreSQL availability check
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://heimdall:heimdall@localhost:5432/heimdall_test",
)

_pg_available: bool | None = None


def pg_is_available() -> bool:
    global _pg_available
    if _pg_available is not None:
        return _pg_available
    try:
        loop = asyncio.new_event_loop()

        async def _probe():
            engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()

        loop.run_until_complete(_probe())
        loop.close()
        _pg_available = True
    except Exception:
        _pg_available = False
    return _pg_available


requires_pg = pytest.mark.skipif(
    not pg_is_available(),
    reason="PostgreSQL not available — set TEST_DATABASE_URL",
)

# ---------------------------------------------------------------------------
# DB engine + fixtures (only initialised when PG is reachable)
# ---------------------------------------------------------------------------

if pg_is_available():
    from app.database import Base

    _engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    _TestSession = async_sessionmaker(
        bind=_engine, class_=AsyncSession, expire_on_commit=False,
    )

    @pytest_asyncio.fixture(scope="session", autouse=True)
    async def _setup_tables():
        """Create all tables at session start, drop at session end."""
        import app.models  # noqa: F401 — populate Base.metadata

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await _engine.dispose()

    @pytest_asyncio.fixture()
    async def db_session():
        """Async session that rolls back after each test."""
        async with _TestSession() as session:
            yield session
            await session.rollback()

    @pytest_asyncio.fixture()
    async def client(db_session: AsyncSession):
        """httpx AsyncClient wired to the FastAPI app with test DB session."""
        from app.database import get_db
        from app.main import app

        async def _override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()

    @pytest_asyncio.fixture()
    async def registered_parent(client: AsyncClient, db_session: AsyncSession):
        """Register a parent user and return context dict.

        Returns dict with keys:
            headers, user_id, family_id, email, tokens
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

else:
    # Stub fixtures so test collection doesn't fail when PG is absent
    @pytest.fixture()
    def db_session():
        pytest.skip("PostgreSQL not available")

    @pytest.fixture()
    def client():
        pytest.skip("PostgreSQL not available")

    @pytest.fixture()
    def registered_parent():
        pytest.skip("PostgreSQL not available")
