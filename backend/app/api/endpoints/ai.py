"""AI explainability endpoints — explain blocked payments, policies,
and summarise audit logs.

**All routes require authentication.**  These endpoints are purely
advisory — AI is **never** involved in payment approval.

If no AI provider is configured, deterministic fallback text is returned
with ``provider: "fallback"``.
"""

from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.api.ai_schemas import AIExplanation, ExplainBlockedRequest, ExplainPolicyRequest
from app.db.session import get_session
from app.services.ai_service import (
    explain_blocked_payment,
    explain_policy,
    summarize_audit,
)

router = APIRouter(prefix="/ai", tags=["ai"])


# =============================================================================
# POST /ai/explain-blocked
# =============================================================================


@router.post(
    "/explain-blocked",
    response_model=AIExplanation,
    summary="Explain why a payment was blocked",
    description="""
Returns a plain-English explanation of a blocked payment, using AI when
available or a deterministic fallback otherwise.

Send the blocked payment's details (request_id, agent name, merchant name,
amount, and rejection reason).  The response explains what rule was violated
and what the owner can do.
""",
)
async def explain_blocked(
    body: ExplainBlockedRequest,
    session = Depends(get_session),
) -> dict[str, str]:
    """Explain a blocked payment."""
    explanation = await explain_blocked_payment(
        reason=body.reason,
        agent_name=body.agent_name,
        merchant_name=body.merchant_name,
        amount=body.amount,
    )
    return _response(explanation)


# =============================================================================
# POST /ai/explain-policy
# =============================================================================


@router.post(
    "/explain-policy",
    response_model=AIExplanation,
    summary="Explain an agent's spending policy in plain English",
    description="""
Returns a plain-English summary of an agent's spending rules, using AI
when available or a deterministic fallback otherwise.

Send the agent's policy details — only the fields you send are used.
""",
)
async def explain_policy_route(
    body: ExplainPolicyRequest,
    session = Depends(get_session),
) -> dict[str, str]:
    """Explain a spending policy."""
    policy: dict[str, Any] = {}
    if body.per_transaction_limit is not None:
        policy["per_transaction_limit"] = body.per_transaction_limit
    if body.daily_limit is not None:
        policy["daily_limit"] = body.daily_limit
    if body.max_requests_per_minute is not None:
        policy["max_requests_per_minute"] = body.max_requests_per_minute
    if body.balance is not None:
        policy["balance"] = body.balance
    if body.status is not None:
        policy["status"] = body.status

    explanation = await explain_policy(body.agent_name, policy)
    return _response(explanation)


# =============================================================================
# GET /ai/summarize-audit
# =============================================================================


@router.get(
    "/summarize-audit",
    response_model=AIExplanation,
    summary="Summarise recent audit log activity",
    description="""
Returns a plain-English summary of recent audit events, using AI when
available or a deterministic fallback otherwise.

### Optional query params
- ``agent_id`` — only include events for this agent
- ``limit`` — max events to summarise (default 50, max 200)
""",
)
async def summarize_audit_route(
    agent_id: int | None = Query(
        default=None, gt=0, description="Filter audit events by agent ID.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    session = Depends(get_session),
) -> dict[str, str]:
    """Summarise recent audit activity."""
    filters = []
    if agent_id is not None:
        filters.append(("actor", "==", f"agent:{agent_id}"))

    # Fetch matching audit events, sort locally and limit
    all_audits = await session.query("audit_events", filters=filters)
    
    def get_timestamp(audit):
        ts = audit.get("timestamp")
        if ts is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if hasattr(ts, "to_datetime"):
            return ts.to_datetime()
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                pass
        return ts
        
    all_audits.sort(key=get_timestamp, reverse=True)
    rows = all_audits[:limit]

    events = [
        {
            "event_type": r.get("event_type"),
            "actor": r.get("actor"),
            "details": r.get("details") or "",
            "timestamp": get_timestamp(r).isoformat(),
        }
        for r in rows
    ]

    explanation = await summarize_audit(events)
    return _response(explanation)


# =============================================================================
# Helper
# =============================================================================


def _response(explanation: str) -> dict[str, str]:
    """Wrap an explanation with the provider type."""
    from app.services.ai_service import _get_provider

    provider = _get_provider()
    return {
        "explanation": explanation,
        "provider": provider.provider_name if provider.is_available else "fallback",
    }
