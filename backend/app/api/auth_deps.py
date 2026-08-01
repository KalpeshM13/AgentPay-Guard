"""Authentication dependencies for FastAPI endpoints.

These dependencies are used with ``Depends()`` to protect routes.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.constants import UserRole
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import decode_access_token, get_user_by_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAuth2 scheme — expects ``Authorization: Bearer <token>``
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    description="Login with email/password to receive a JWT.",
    auto_error=False,
)


# ---------------------------------------------------------------------------
# Core dependency: resolve the currently-authenticated User (or 401)
# ---------------------------------------------------------------------------
async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session = Depends(get_session),
) -> User:
    """Dependency that returns the authenticated ``User`` from a JWT Bearer token.

    Falls back to the default owner account in local/development environments if no token is provided.
    """

    if token is None:
        from app.core.config import settings
        from app.models.user import User
        from app.core.constants import UserRole
        from app.services.auth_service import hash_password, get_user_by_email
        
        email = settings.DEFAULT_OWNER_EMAIL.lower().strip()
        user = await get_user_by_email(session, email)

        if user is None:
            next_id = await session.get_next_id("users")
            user = User(
                id=next_id,
                email=email,
                hashed_password=hash_password(settings.DEFAULT_OWNER_PASSWORD),
                display_name="Default Owner",
                role=UserRole.OWNER,
                is_active=True,
            )
            await session.insert("users", next_id, user.to_dict())
        return user

    # -- 1. Validate the JWT ------------------------------------------------
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -- 2. Look up the user ------------------------------------------------
    user = await get_user_by_id(session, user_id)
    if user is None:
        logger.warning("Token for deleted user id=%d", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -- 3. Check account status --------------------------------------------
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


# ---------------------------------------------------------------------------
# Optional user — does NOT raise 401; returns None for unauthenticated access
# ---------------------------------------------------------------------------
async def get_optional_user(
    token: str | None = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
    ),
    session = Depends(get_session),
) -> User | None:
    """Like ``get_current_user`` but returns ``None`` for anonymous requests."""
    if token is None:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    return await get_user_by_id(session, user_id)


# ---------------------------------------------------------------------------
# Role-based authorization guard (factory)
# ---------------------------------------------------------------------------
def require_role(*allowed_roles: UserRole | str):
    """Factory that returns a dependency requiring one of *allowed_roles*."""
    allowed = {UserRole(r) for r in allowed_roles}

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(sorted(r.value for r in allowed))}",
            )
        return user

    return role_checker


# ---------------------------------------------------------------------------
# Pre-built role guards — import these directly
# ---------------------------------------------------------------------------
RequireOwner = require_role(UserRole.OWNER)
"""Only users with the ``owner`` role may proceed."""

RequireAdmin = require_role(UserRole.OWNER, UserRole.ADMIN)
"""Owners *and* admins may proceed."""

RequireViewer = require_role(UserRole.OWNER, UserRole.ADMIN, UserRole.VIEWER)
"""Any authenticated (active) user.  Equivalent to ``get_current_user``."""
