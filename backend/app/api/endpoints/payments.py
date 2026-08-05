"""Payment endpoint — the agent-facing ``POST /payments`` route.

This is a **thin** router: it loads models, delegates to the policy engine,
and then delegates to the payment executor.  No business logic lives here.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.payment_schemas import PaymentRequestSchema, PaymentResponse
from app.db.session import get_session
from app.services import agent_service, allowlist_service, merchant_service
from app.services.payment_executor import (
    count_recent_requests,
    execute,
    get_daily_spend,
    is_duplicate_request_id,
)
from app.services.policy_engine import PolicyContext, PolicyDecision, evaluate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])



@router.post(
    "/payments",
    response_model=PaymentResponse,
    summary="Agent requests a payment",
    description="""
The agent sends a payment request.  The endpoint:

1. Loads the agent, merchant, and allowlist status.
2. Runs the **Policy Engine** (all 10 checks).
3. If BLOCKED, records the blocked PaymentRequest + audit log and returns the reason.
4. If APPROVED, delegates to the **Payment Executor** to debit
   the simulated wallet and record the transaction.

**No authentication required** — this is the agent-facing endpoint.
The agent has no credentials and cannot bypass policy.
""",
    responses={
        200: {"description": "Payment settled (or blocked with reason)."},
        404: {"description": "Agent or merchant not found."},
        422: {"description": "Validation error."},
    },
)
async def request_payment(
    body: PaymentRequestSchema,
    session = Depends(get_session),
) -> PaymentResponse:
    """Process a payment request through the policy + executor pipeline."""

    if body.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="amount must be positive.",
        )

    agent = await agent_service.get_agent_by_id(session, body.agent_id)
    merchant = await merchant_service.get_merchant_by_id(session, body.merchant_id)

    is_allowlisted = False
    if agent is not None and merchant is not None:
        entry = await allowlist_service.get_allowlist_entry(
            session, body.agent_id, body.merchant_id,
        )
        is_allowlisted = entry is not None

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=1)

    ctx = PolicyContext(
        request_id=body.request_id,
        request_timestamp=now,
        agent=agent,
        merchant=merchant,
        is_merchant_allowlisted=is_allowlisted,
        amount=body.amount,
        get_daily_spend=lambda aid: get_daily_spend(session, aid),
        count_recent_requests=lambda aid, ts: count_recent_requests(session, aid, window_start),
        is_duplicate_request_id=lambda rid: is_duplicate_request_id(session, rid),
    )

    decision: PolicyDecision = await evaluate(ctx)


    if not decision.approved:
        if decision.reason == 'DUPLICATE_REQUEST':
            await _record_duplicate_blocked(session, body)
        else:
            await _record_blocked(session, body, decision.reason or "UNKNOWN")
        return PaymentResponse(
            request_id=body.request_id,
            status="BLOCKED",
            reason=decision.reason,
            amount=body.amount,
        )

    assert agent is not None, "policy should have rejected missing agent"
    transaction = await execute(
        session=session,
        agent=agent,
        request_id=body.request_id,
        merchant_id=body.merchant_id,
        amount=body.amount,
    )

    spent_today = await get_daily_spend(session, agent.id)
    remaining = max(0.0, agent.daily_limit - spent_today)

    return PaymentResponse(
        request_id=body.request_id,
        status="SETTLED",
        amount=body.amount,
        balance_after=agent.balance,
        remaining_daily_limit=remaining,
    )



async def _record_duplicate_blocked(
    session,
    body: PaymentRequestSchema,
) -> None:
    """Log a duplicate-request block (no new PaymentRequest — already exists)."""
    import json

    from app.core.constants import AuditEventType
    from app.models.audit_log import AuditLog

    audit_id = await session.get_next_id("audit_events")
    audit = AuditLog(
        id=audit_id,
        actor=f"agent:{body.agent_id}",
        event_type=AuditEventType.PAYMENT_BLOCKED.value,
        details=json.dumps({
            "request_id": body.request_id,
            "agent_id": body.agent_id,
            "merchant_id": body.merchant_id,
            "amount": body.amount,
            "reason": "DUPLICATE_REQUEST",
            "note": "Original PaymentRequest already exists.",
        }),
    )
    await session.insert("audit_events", audit_id, audit.to_dict())
    logger.info("Duplicate payment blocked: request=%s", body.request_id)


async def _record_blocked(
    session: any,
    body: PaymentRequestSchema,
    reason: str,
) -> None:
    """Persist a BLOCKED PaymentRequest + AuditLog in Firestore (fire-and-forget)."""
    import json
    from datetime import datetime, timezone

    from app.core.constants import AuditEventType
    from app.models.audit_log import AuditLog
    from app.models.payment_request import PaymentRequest

    results = await session.query("payment_requests", [("request_id", "==", body.request_id)])

    if not results:
        pr_id = await session.get_next_id("payment_requests")
        pr = PaymentRequest(
            id=pr_id,
            request_id=body.request_id,
            agent_id=body.agent_id,
            merchant_id=body.merchant_id,
            amount=body.amount,
            status="BLOCKED",
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        await session.insert("payment_requests", pr_id, pr.to_dict())

    audit_id = await session.get_next_id("audit_events")
    audit = AuditLog(
        id=audit_id,
        actor=f"agent:{body.agent_id}",
        event_type=AuditEventType.PAYMENT_BLOCKED.value,
        details=json.dumps({
            "request_id": body.request_id,
            "agent_id": body.agent_id,
            "merchant_id": body.merchant_id,
            "amount": body.amount,
            "reason": reason,
        }),
        timestamp=datetime.now(timezone.utc),
    )
    await session.insert("audit_events", audit_id, audit.to_dict())
    logger.info(
        "Payment BLOCKED: request=%s reason=%s", body.request_id, reason,
    )
