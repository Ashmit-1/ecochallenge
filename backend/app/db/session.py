"""Database engine and session dependency."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from sqlalchemy import Engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.sqlalchemy_url.startswith("sqlite")

engine = create_engine(
    settings.sqlalchemy_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=StaticPool if settings.sqlalchemy_url in {"sqlite://", "sqlite:///:memory:"} else None,
)


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection: object, _connection_record: object) -> None:
    """SQLite ignores foreign keys unless asked, and locks instantly without a busy timeout."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
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
