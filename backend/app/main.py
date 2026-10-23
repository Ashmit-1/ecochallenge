"""Application factory and global wiring."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1.router import api_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)

DESCRIPTION = """
Turn everyday sustainable habits into visible progress.

Students browse environmental challenges, complete them in the real world, and upload a photo as
evidence. An AI vision model checks the photo against the claimed activity before points are
awarded. Points feed a profile, badges, estimated CO₂ savings, and a leaderboard.

**AI checks are a deterrent, not proof.** CO₂ figures are estimates.
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    if settings.vision_provider == "gemini" and not settings.gemini_api_key:
        logger.warning(
            "VISION_PROVIDER=gemini but GEMINI_API_KEY is empty. "
            "Submissions will return 502 until a key is added, or set VISION_PROVIDER=mock."
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_request, exc: IntegrityError) -> JSONResponse:
        # Last line of defence: services handle the conflicts they can explain.
        logger.warning("Unhandled integrity error: %s", exc)
        return JSONResponse(
            status_code=409,
            content={"detail": "That change conflicts with existing data."},
        )

    return app


app = create_app()
