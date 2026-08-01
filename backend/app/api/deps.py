"""Shared FastAPI dependencies.

Single import point for session, auth, and role guards.

Usage::

    from app.api.deps import get_current_user, get_session, RequireAdmin
"""

from app.api.auth_deps import (   # noqa: F401  # re-exported
    RequireAdmin,
    RequireOwner,
    RequireViewer,
    get_current_user,
    get_optional_user,
    require_role,
)
from app.db.session import get_session  # noqa: F401  # re-exported

__all__ = [
    "get_session",
    "get_current_user",
    "get_optional_user",
    "RequireAdmin",
    "RequireOwner",
    "RequireViewer",
    "require_role",
]
