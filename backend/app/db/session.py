from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

_database_url = settings.normalized_database_url
_is_sqlite = _database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Phase 11 (spec §7): SQLite has no real pool to configure (NullPool-equivalent single-file
# access) — pool_size/max_overflow/etc. are Postgres-only kwargs and SQLAlchemy rejects them for
# the SQLite dialect's default pool class, so they're only passed for a real database.
_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout_seconds,
        "pool_recycle": settings.db_pool_recycle_seconds,
        "pool_pre_ping": settings.db_pool_pre_ping,
    }
)

engine = create_async_engine(_database_url, echo=False, connect_args=connect_args, **_pool_kwargs)

if _is_sqlite:
    # SQLite does NOT enforce foreign keys by default — every ondelete=CASCADE/RESTRICT/SET NULL
    # in app/models/*.py is silently decorative without this (Phase 9.5 audit finding: a company
    # with jobs could be deleted with no error, leaving jobs.company_id pointing at nothing,
    # despite the FK being declared RESTRICT). Postgres enforces this natively; this only matters
    # because SQLite is what dev/test actually run against in this environment (see
    # PROJECT_STATUS.md — Docker/Postgres has never been verified here).
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
