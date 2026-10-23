"""Health and metadata contracts."""

from __future__ import annotations

from app.schemas.common import APIModel


class HealthResponse(APIModel):
    status: str
    database: str
    version: str


class MetaResponse(APIModel):
    name: str
    version: str
    verification_provider: str
    verification_disclaimer: str
    environmental_disclaimer: str
    api_docs: str
