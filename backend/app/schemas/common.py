"""Shared schema primitives."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _serialize_utc(value: datetime) -> str:
    """Write timestamps as unambiguous ISO-8601 with a Z suffix."""
    if value.tzinfo is None:  # defensive: a naive value is still treated as UTC
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


# Use everywhere a timestamp is returned. SQLite stores no offset, so the model layer re-attaches
# UTC on read; this serializer guarantees the wire format always ends in Z.
UTCDateTime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc, return_type=str, when_used="json"),
]


class APIModel(BaseModel):
    """Base for every response/request DTO."""

    model_config = ConfigDict(from_attributes=True)
