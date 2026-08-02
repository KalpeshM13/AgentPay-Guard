"""Shared FastAPI dependencies.

Single import point for session, auth, and role guards.

Usage::

    from app.api.deps import get_current_user, get_session, RequireAdmin
"""

from app.db.session import get_session  # noqa: F401  # re-exported

__all__ = [
    "get_session",
]
