"""Authentication request/response contracts."""

from __future__ import annotations

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel, UTCDateTime

# Letters, digits, spaces, and . _ - ' only. Keeps leaderboard names readable and printable.
DISPLAY_NAME_PATTERN = r"^[\w .'\-]{2,30}$"


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=30, pattern=DISPLAY_NAME_PATTERN)

    @field_validator("display_name", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class UpdateProfileRequest(APIModel):
    display_name: str | None = Field(
        default=None, min_length=2, max_length=30, pattern=DISPLAY_NAME_PATTERN
    )

    @field_validator("display_name", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class UserRead(APIModel):
    id: int
    email: EmailStr
    display_name: str
    points_total: int
    created_at: UTCDateTime


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
