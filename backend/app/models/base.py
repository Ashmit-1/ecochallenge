"""Shared model helpers."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp.

    SQLModel 0.0.48 maps ``datetime`` fields to its ``UTCDateTime`` type, which **requires** an
    aware value on write and re-attaches UTC on read (SQLite stores no offset itself). Returning a
    naive value here fails at flush time, so every timestamp in this project is aware UTC.
    """
    return datetime.now(UTC)
