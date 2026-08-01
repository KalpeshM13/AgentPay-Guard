"""Authentication endpoints — register, login, and current-user lookup.

All three routes are public (no auth required for register/login; /me
requires a valid token through the dependency chain).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm


from app.api.auth_deps import get_current_user
from app.api.auth_schemas import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_user_by_email,
    register_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =========================================================================
# POST /auth/register
# =========================================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="""
Creates a new user account with a bcrypt-hashed password.

**Default role** is ``viewer`` (the first registered user may be promoted
to ``owner`` manually, or via the ``DEFAULT_OWNER_*`` env vars).

### Rules
- ``email`` must be globally unique.
- ``password`` must be 6–128 characters.
- ``display_name`` is shown in the dashboard UI.
""",
    responses={
        201: {"description": "User created successfully."},
        409: {"description": "Email already registered."},
        422: {"description": "Validation error (bad email, short password, etc.)."},
    },
)
async def register(
    body: RegisterRequest,
    session = Depends(get_session),
) -> User:
    """Register a new user."""
    # -- Duplicate check ----------------------------------------------------
    existing = await get_user_by_email(session, body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # -- Create the user ----------------------------------------------------
    user = await register_user(
        session,
        email=body.email,
        plain_password=body.password,
        display_name=body.display_name,
    )
    return user


# =========================================================================
# POST /auth/login
# =========================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT access token",
    description="""
Authenticates with email + password and returns a signed JWT.

The token must be sent in the ``Authorization`` header as
``Bearer <token>`` on all protected routes.

### OAuth2-compatible
Uses ``application/x-www-form-urlencoded`` with fields ``username``
(email) and ``password``.  The **Authorize** button in Swagger uses
this endpoint automatically.

### Example (curl)

    curl -X POST http://localhost:8000/api/v1/auth/login \\
      -d 'username=admin@agentpay.dev&password=admin123'

""",
    responses={
        200: {"description": "Login successful; JWT returned."},
        401: {"description": "Invalid email or password."},
    },
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session = Depends(get_session),
) -> dict:
    """Authenticate via OAuth2 password flow and return a JWT access token."""
    user = await authenticate_user(session, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_in = create_access_token(user.id)
    logger.info("User %d (%s) logged in", user.id, user.email)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


# =========================================================================
# GET /auth/me
# =========================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently-authenticated user",
    description="""
Returns the profile of the user identified by the Bearer token in the
``Authorization`` header.

Use this to verify the token is valid and to retrieve the current user's
role and permissions.
""",
    responses={
        200: {"description": "Current user profile."},
        401: {"description": "Missing or invalid token."},
    },
)
async def whoami(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user's profile."""
    return current_user
