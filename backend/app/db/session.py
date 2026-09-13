from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_async_engine(settings.database_url, echo=False, connect_args=connect_args)

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
