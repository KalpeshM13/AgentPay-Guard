"""Authentication-related Pydantic schemas.

These schemas drive the automatic Swagger documentation:
- ``RegisterRequest``  → ``POST /auth/register``  request body
- ``LoginRequest``     → ``POST /auth/login``      request body (form-encoded)
- ``TokenResponse``    → response of login
- ``UserResponse``     → response of ``GET /auth/me``
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.constants import UserRole


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Body for ``POST /auth/register``.

    Example:
        {
            "email": "owner@agentpay.dev",
            "password": "s3cret!",
            "display_name": "Alice"
        }
    """
    email: EmailStr = Field(
        ...,
        examples=["alice@agentpay.dev"],
        description="Unique email address used for login.",
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        examples=["s3cret-p4ss"],
        description="Plain-text password (hashed server-side with bcrypt).",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Alice"],
        description="Human-readable name shown in the dashboard.",
    )


class LoginRequest(BaseModel):
    """Body for ``POST /auth/login``.

    Use ``application/x-www-form-urlencoded`` (OAuth2-compatible).

    Example:
        username=alice@agentpay.dev&password=s3cret-p4ss
    """
    username: str = Field(
        ...,
        examples=["alice@agentpay.dev"],
        description="Registered email address.",
    )
    password: str = Field(
        ...,
        examples=["s3cret-p4ss"],
        description="Account password.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Returned after a successful login.

    Example:
        {
            "access_token": "eyJ...",
            "token_type": "bearer",
            "expires_in": 3600
        }
    """
    access_token: str = Field(
        ...,
        examples=["eyJhbGciOiJIUzI1NiIs..."],
        description="Signed JWT used as the Bearer token.",
    )
    token_type: str = Field(
        default="bearer",
        examples=["bearer"],
        description="Always ``bearer`` (RFC 6750).",
    )
    expires_in: int = Field(
        ...,
        examples=[3600],
        description="Seconds until the token expires (from ``iat``).",
    )


class UserResponse(BaseModel):
    """Public representation of the currently-authenticated user.

    Example:
        {
            "id": 1,
            "email": "alice@agentpay.dev",
            "display_name": "Alice",
            "role": "owner",
            "is_active": true,
            "created_at": "2026-08-01T14:30:00Z"
        }
    """
    id: int
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    balance: float
    created_at: datetime

    model_config = {"from_attributes": True}
