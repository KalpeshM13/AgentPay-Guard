"""Dashboard-related Pydantic response schemas.

Used by ``GET /dashboard/summary``, ``/dashboard/activity``, and ``/dashboard/audit``.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# GET /dashboard/summary
# =============================================================================


class DashboardSummary(BaseModel):
    """Top-level KPIs for the owner dashboard.

    Example:
        {
            "total_agents": 5,
            "frozen_agents": 1,
            "active_agents": 4,
            "total_balance": 45000.0,
            "today_spending": 1250.0,
            "today_settled_count": 3,
            "today_blocked_count": 2
        }
    """
    total_agents: int = Field(..., examples=[5])
    frozen_agents: int = Field(..., examples=[1])
    active_agents: int = Field(..., examples=[4])
    total_balance: float = Field(..., examples=[45_000.0])
    today_spending: float = Field(..., examples=[1_250.0])
    today_settled_count: int = Field(..., examples=[3])
    today_blocked_count: int = Field(..., examples=[2])


# =============================================================================
# GET /dashboard/activity
# =============================================================================


class ActivityItem(BaseModel):
    """A single payment request shown in the live activity feed.

    Example:
        {
            "id": 42,
            "request_id": "req_1042",
            "agent_id": 1,
            "agent_name": "ShoppingAgent-01",
            "merchant_id": 2,
            "amount": 300.0,
            "status": "SETTLED",
            "reason": null,
            "timestamp": "2026-08-01T14:32:16Z"
        }
    """
    id: int
    request_id: str
    agent_id: int | None
    agent_name: str | None = Field(
        default=None,
        description="Agent display name (null if agent was deleted).",
    )
    merchant_id: int | None
    amount: float
    status: str
    reason: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class ActivityResponse(BaseModel):
    """Paginated activity-feed response."""
    total: int = Field(..., examples=[150])
    items: list[ActivityItem]


class ActivityFilter(BaseModel):
    """Optional query filters for ``GET /dashboard/activity``.

    All fields are optional — omit to get everything.
    """
    agent_id: int | None = Field(
        default=None, gt=0,
        description="Filter by agent ID.",
    )
    status: str | None = Field(
        default=None,
        examples=["SETTLED", "BLOCKED"],
        description="Filter by payment status.",
    )
    limit: int = Field(
        default=50, ge=1, le=200,
        description="Max items to return.",
    )


# =============================================================================
# GET /dashboard/audit
# =============================================================================


class AuditItem(BaseModel):
    """A single audit-log entry.

    Example:
        {
            "id": 100,
            "actor": "agent:1",
            "event_type": "payment_settled",
            "details": "{\"request_id\": \"req_1042\", ...}",
            "timestamp": "2026-08-01T14:32:16Z"
        }
    """
    id: int
    actor: str
    event_type: str
    details: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditResponse(BaseModel):
    """Paginated audit-log response."""
    total: int = Field(..., examples=[500])
    items: list[AuditItem]


class AuditFilter(BaseModel):
    """Optional query filters for ``GET /dashboard/audit``."""
    event_type: str | None = Field(
        default=None,
        examples=["payment_settled", "payment_blocked", "agent_frozen"],
        description="Filter by audit event type.",
    )
    limit: int = Field(
        default=50, ge=1, le=200,
        description="Max items to return.",
    )
