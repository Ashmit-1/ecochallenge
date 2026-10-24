"""Database engine and session dependency.

Local development and tests use SQLite through the standard ``sqlite3`` driver. Production uses
Turso (hosted libSQL) through the same SQLModel code, selected entirely by ``DATABASE_URL``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import Engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool, StaticPool
from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()

_MEMORY_URLS = {"sqlite://", "sqlite:///:memory:", "sqlite+libsql://"}


def _connect_args(url: str, *, auth_token: str = "") -> dict[str, object]:
    """Driver arguments for whichever backend the URL selects.

    Remote libSQL needs its auth token; a local ``sqlite3`` connection is shared across the
    threadpool, so ``check_same_thread`` must be off.
    """
    if url.startswith("sqlite+libsql://"):
        if not auth_token and urlparse(url).hostname:
            raise RuntimeError(
                "TURSO_AUTH_TOKEN is required when DATABASE_URL points at a libSQL host."
            )
        return {"auth_token": auth_token} if auth_token else {}
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def build_engine(
    url: str, *, auth_token: str | None = None, poolclass: type[Pool] | None = None
) -> Engine:
    """Create an engine for a normalised SQLAlchemy URL.

    Alembic reuses this so migrations authenticate to the same database exactly like the app.
    """
    if poolclass is None and url in _MEMORY_URLS:
        poolclass = StaticPool
    if auth_token is None:
        auth_token = settings.turso_auth_token
    return create_engine(
        url, connect_args=_connect_args(url, auth_token=auth_token), poolclass=poolclass
    )


engine = build_engine(settings.sqlalchemy_url)


def _is_libsql_connection(dbapi_connection: object) -> bool:
    module = type(dbapi_connection).__module__ or ""
    return module.startswith("libsql_experimental")


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection: object, _connection_record: object) -> None:
    """SQLite ignores foreign keys unless asked, and locks instantly without a busy timeout."""
    is_sqlite3 = isinstance(dbapi_connection, sqlite3.Connection)
    if not is_sqlite3 and not _is_libsql_connection(dbapi_connection):
        return
    connection: Any = dbapi_connection
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    if is_sqlite3:
        # A per-connection timeout is meaningless for a remote server.
        cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as session:
        yield session
