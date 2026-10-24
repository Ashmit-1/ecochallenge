"""Application configuration, loaded from environment / backend/.env."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# .../global_warming_project/backend
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All runtime configuration. See backend/.env.example for documentation."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "EcoChallenge"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'ecochallenge.db'}"
    # Required when DATABASE_URL points at a Turso/libSQL host; unused for a local file.
    turso_auth_token: str = ""
    uploads_dir: Path = Path("./uploads")
    max_upload_mb: int = 6

    # --- Browser session cookies (frontend uses httpOnly cookies, not localStorage) ---
    access_cookie_name: str = "ecochallenge_access"
    csrf_cookie_name: str = "ecochallenge_csrf"
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    # None = secure only in production. Set explicitly only for unusual local HTTPS setups.
    cookie_secure: bool | None = None

    vision_provider: Literal["gemini", "mock"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemma-4-26b-a4b-it"  # verified to support image + JSON schema
    vision_timeout_seconds: float = 30.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> object:
        """Accept comma-separated strings, JSON arrays, or real lists."""
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                return json.loads(raw)
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return value

    @property
    def is_libsql(self) -> bool:
        """True when the database is opened through the libSQL driver (local or Turso)."""
        return self.database_url.startswith(("libsql://", "sqlite+libsql://"))

    @property
    def sqlalchemy_url(self) -> str:
        """Normalise ``DATABASE_URL`` into a URL SQLAlchemy can open.

        Local SQLite paths become absolute so the CWD never changes which DB is opened.
        A Turso ``libsql://`` URL gains the dialect prefix and TLS.
        """
        url = self.database_url
        if url.startswith("sqlite+libsql://"):
            return url
        if url.startswith("libsql://"):
            host = url[len("libsql://") :]
            separator = "&" if "?" in host else "?"
            return f"sqlite+libsql://{host}{separator}secure=true"
        prefix = "sqlite:///"
        if not url.startswith(prefix):
            return url
        raw_path = url[len(prefix) :]
        if raw_path.startswith("/") or raw_path == ":memory:":
            return url
        return f"{prefix}{BACKEND_DIR / raw_path}"

    @property
    def uploads_path(self) -> Path:
        path = self.uploads_dir
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def use_secure_cookies(self) -> bool:
        return self.cookie_secure if self.cookie_secure is not None else self.is_production

    @property
    def access_token_max_age(self) -> int:
        return self.access_token_expire_minutes * 60


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Tests override dependencies, not this object."""
    return Settings()
