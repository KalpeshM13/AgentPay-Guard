"""Authentication dependencies for FastAPI endpoints.

These dependencies are used with ``Depends()`` to protect routes.

Quick-reference:

    from app.api.auth_deps import get_current_user, require_role

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)): ...

    @router.post("/admin-only")
    async def admin_only(user: User = Depends(require_role("admin"))): ...
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

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
)


# ---------------------------------------------------------------------------
# Core dependency: resolve the currently-authenticated User (or 401)
# ---------------------------------------------------------------------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dependency that returns the authenticated ``User`` from a JWT Bearer token.

    Raises ``401 Unauthorized`` if:
    - the token is missing / malformed / expired
    - the user does not exist in the database
    - the user account is deactivated
    """

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
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Like ``get_current_user`` but returns ``None`` for anonymous requests.

    Useful for endpoints that behave differently for authenticated users.
    """
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
    """Factory that returns a dependency requiring one of *allowed_roles*.

    ***Order matters*** — this dependency **must** be called *after*
    ``get_current_user`` (i.e. ``get_current_user`` resolves the user, then
    ``require_role`` checks the role).

    Usage::

        OwnerOrAdmin = require_role("owner", "admin")

        @router.delete("/agents/{id}")
        async def delete_agent(
            agent_id: str,
            user: User = Depends(get_current_user),
            _: None = Depends(OwnerOrAdmin),
        ): ...

    Or use the convenience pre-built guards below.
    """
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
