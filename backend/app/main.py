"""Application factory and global wiring."""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.v1.router import api_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Allow multipart boundaries/headers on top of the photo itself.
_MULTIPART_OVERHEAD_BYTES = 256 * 1024

DESCRIPTION = """
Turn everyday sustainable habits into visible progress.

Students browse environmental challenges, complete them in the real world, and upload a photo as
evidence. An AI vision model checks the photo against the claimed activity before points are
awarded. Points feed a profile, badges, estimated CO₂ savings, and a leaderboard.

**AI checks are a deterrent, not proof.** CO₂ figures are estimates.
"""


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject an oversized body before Starlette parses and spools it to disk.

    The upload handler also checks the size, but by then the whole multipart body has already been
    consumed. This is the cheap first line of defence for clients that send ``Content-Length``;
    a reverse proxy still needs its own limit for chunked bodies.
    """

    def __init__(self, app: ASGIApp, overhead_bytes: int = 0) -> None:
        super().__init__(app)
        self.overhead_bytes = overhead_bytes

    async def dispatch(self, request, call_next):  # noqa: ANN001
        # Read settings per request so tests and config changes are honoured.
        limit = get_settings().max_upload_bytes + self.overhead_bytes
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                length = int(declared)
            except ValueError:
                length = 0
            if length > limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large."},
                )
        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie check for cookie-authenticated, state-changing requests.

    Bearer requests are exempt: a token that the browser does not attach automatically cannot be
    replayed cross-site. Login/register are exempt because no session exists yet.
    """

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

    async def dispatch(self, request, call_next):  # noqa: ANN001
        settings = get_settings()
        exempt = {
            f"{settings.api_v1_prefix}/auth/login",
            f"{settings.api_v1_prefix}/auth/register",
        }
        uses_bearer = request.headers.get("authorization", "").lower().startswith("bearer ")
        has_session_cookie = bool(request.cookies.get(settings.access_cookie_name))

        if (
            request.method not in self.SAFE_METHODS
            and request.url.path not in exempt
            and not uses_bearer
            and has_session_cookie
        ):
            header_token = request.headers.get("x-csrf-token")
            cookie_token = request.cookies.get(settings.csrf_cookie_name)
            if (
                not header_token
                or not cookie_token
                or not secrets.compare_digest(header_token, cookie_token)
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF validation failed. Reload the app and try again."
                    },
                )

        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    if settings.vision_provider == "gemini" and not settings.gemini_api_key:
        logger.warning(
            "VISION_PROVIDER=gemini but GEMINI_API_KEY is empty. "
            "Submissions will return 502 until a key is added, or set VISION_PROVIDER=mock."
        )
    if settings.vision_provider == "openai" and (not settings.openai_api_key or not settings.openai_base_url):
        logger.warning(
            "VISION_PROVIDER=openai but OPENAI_API_KEY or OPENAI_BASE_URL is empty. "
            "Submissions will return 502 until configured, or set VISION_PROVIDER=mock."
        )
    if settings.storage_backend == "r2" and not settings.r2_configured:
        logger.warning(
            "STORAGE_BACKEND=r2 but the R2 settings are incomplete. "
            "Uploads and photo reads will fail until they are set."
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

    # Added first = innermost; CORS added last so error responses still carry CORS headers.
    app.add_middleware(
        RequestBodyLimitMiddleware, overhead_bytes=_MULTIPART_OVERHEAD_BYTES
    )
    app.add_middleware(CSRFMiddleware)
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
