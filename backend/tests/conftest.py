import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.security.rate_limit import reset_all_rate_limiters

# SQLite in-memory is the default fast path. Set TEST_DATABASE_URL to a postgresql+asyncpg:// URL to
# run the same suite against PostgreSQL for production parity (Phase 11 §6) — see DATABASE.md.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite://")
_IS_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")
_pg_schema_ready = False

if _IS_POSTGRES and os.environ.get("PGLITE_SOCKET_SHIM") == "1":
    # Harness-only workaround, never used by the application: the PGlite socket server (PostgreSQL
    # compiled to WASM, used because no native Postgres exists in this environment) never closes its
    # side of the socket after a client Terminate, so asyncpg's graceful close() waits forever.
    # terminate() closes the transport immediately. Real Postgres servers do not need this.
    import asyncpg

    async def _terminate_instead_of_close(self, *, timeout=None) -> None:
        self.terminate()

    asyncpg.connection.Connection.close = _terminate_instead_of_close


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    # The rate limiters are process-global (Phase 11) — without this, a long test run would
    # eventually trip a 429 on a perfectly legitimate test that just happens to be the Nth to hit
    # /auth/login or /auth/register in this pytest process.
    reset_all_rate_limiters()


async def _prepare_postgres_schema(engine) -> None:
    """Create the schema once per pytest run, then empty every table before each test — dropping
    and recreating 45 tables per test would be needlessly slow on a real server too."""
    global _pg_schema_ready
    async with engine.begin() as conn:
        if not _pg_schema_ready:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            _pg_schema_ready = True
        else:
            tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    if _IS_POSTGRES:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        await _prepare_postgres_schema(engine)
    else:
        engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Mirrors app/db/session.py's production engine setup — SQLite doesn't enforce foreign
        # keys by default, so tests would otherwise silently pass with orphaned/CASCADE-violating
        # rows that a real Postgres deployment would reject (Phase 9.5 audit finding).
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as session:
        yield session

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
