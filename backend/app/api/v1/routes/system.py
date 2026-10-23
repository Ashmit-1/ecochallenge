"""Health and public metadata (no auth)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.schemas.system import HealthResponse, MetaResponse
from app.vision.base import VisionConfigurationError
from app.vision.factory import get_vision_provider

router = APIRouter(tags=["system"])

VERIFICATION_DISCLAIMER = (
    "Photo checks are AI-assisted and can make mistakes. An approval means the photo looked "
    "consistent with the activity — it is not proof that the activity happened."
)

ENVIRONMENTAL_DISCLAIMER = (
    "CO₂ figures are estimates based on documented assumptions, not measurements."
)


@router.get("/health", response_model=HealthResponse, summary="Service and database health")
def health(session: SessionDep) -> HealthResponse:
    settings = get_settings()
    try:
        session.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:  # noqa: BLE001 - health checks must not raise a 500
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable.",
        ) from exc

    return HealthResponse(status="ok", database=database, version=settings.app_version)


@router.get("/meta", response_model=MetaResponse, summary="App metadata and disclaimers")
def meta() -> MetaResponse:
    settings = get_settings()
    provider = get_vision_provider()
    try:
        provider_name = provider.name
    except VisionConfigurationError:
        provider_name = settings.vision_provider

    return MetaResponse(
        name=settings.app_name,
        version=settings.app_version,
        verification_provider=provider_name,
        verification_disclaimer=VERIFICATION_DISCLAIMER,
        environmental_disclaimer=ENVIRONMENTAL_DISCLAIMER,
        api_docs="/docs",
    )
