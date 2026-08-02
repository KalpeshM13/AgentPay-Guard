"""Dashboard read-only endpoints — summary KPIs, activity feed, audit log.

All routes require authentication.  Read access is open to any
authenticated user; mutations use the admin/owner guards from ``deps``.

Thin router: delegates everything to ``dashboard_service``.
"""

from fastapi import APIRouter, Depends, Query


from app.api.auth_deps import get_current_user
from app.api.dashboard_schemas import (
    ActivityResponse,
    AuditResponse,
    DashboardSummary,
)
from app.db.session import get_session
from app.models.user import User
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# =============================================================================
# GET /dashboard/summary
# =============================================================================


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard KPIs",
    description="""
Returns the high-level metrics the owner dashboard needs:

- Total / frozen / active agent counts
- Total balance across all agents
- Today's total settled spending
- Counts of today's settled and blocked requests
""",
)
async def summary(
    session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DashboardSummary:
    """Return dashboard KPIs."""
    data = await dashboard_service.get_summary(session, user_id=user.id)
    return DashboardSummary(**data)


# =============================================================================
# GET /dashboard/activity
# =============================================================================


@router.get(
    "/activity",
    response_model=ActivityResponse,
    summary="Get recent payment activity",
    description="""
Returns the most recent payment requests (SETTLED and BLOCKED),
newest first.  Each item includes the agent's display name.

Optional query filters:

- ``agent_id`` — show only this agent's requests
- ``status`` — filter by SETTLED / BLOCKED
- ``limit`` — max items (default 50, max 200)
""",
)
async def activity(
    agent_id: int | None = Query(
        default=None, gt=0, description="Filter by agent ID.",
    ),
    status: str | None = Query(
        default=None,
        examples=["SETTLED", "BLOCKED"],
        description="Filter by payment status.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ActivityResponse:
    """Return recent payment activity."""
    items, total = await dashboard_service.get_activity(
        session, agent_id=agent_id, status_filter=status, limit=limit, user_id=user.id,
    )
    return ActivityResponse(total=total, items=items)


# =============================================================================
# GET /dashboard/audit
# =============================================================================


@router.get(
    "/audit",
    response_model=AuditResponse,
    summary="Get recent audit log entries",
    description="""
Returns the most recent audit-log entries, newest first.

Optional query filters:

- ``event_type`` — e.g. ``payment_settled``, ``payment_blocked``, ``agent_frozen``
- ``limit`` — max items (default 50, max 200)
""",
)
async def audit_log(
    event_type: str | None = Query(
        default=None,
        examples=["payment_settled", "payment_blocked", "agent_frozen"],
        description="Filter by audit event type.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AuditResponse:
    """Return recent audit log entries."""
    items, total = await dashboard_service.get_audit(
        session, event_type=event_type, limit=limit, user_id=user.id,
    )
    return AuditResponse(total=total, items=items)
