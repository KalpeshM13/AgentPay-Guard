"""Payment endpoint — the agent-facing ``POST /payments`` route.

This is a **thin** router: it loads models, delegates to the policy engine,
and then delegates to the payment executor.  No business logic lives here.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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


# =============================================================================
# POST /payments
# =============================================================================

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
    session: AsyncSession = Depends(get_session),
) -> PaymentResponse:
    """Process a payment request through the policy + executor pipeline."""

    # ── 0. Validate amount ─────────────────────────────────────────────
    if body.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="amount must be positive.",
        )

    # ── 1. Load entities ───────────────────────────────────────────────
    agent = await agent_service.get_agent_by_id(session, body.agent_id)
    merchant = await merchant_service.get_merchant_by_id(session, body.merchant_id)

    # ── 2. Check allowlist status ──────────────────────────────────────
    is_allowlisted = False
    if agent is not None and merchant is not None:
        entry = await allowlist_service.get_allowlist_entry(
            session, body.agent_id, body.merchant_id,
        )
        is_allowlisted = entry is not None

    # ── 3. Policy evaluation ───────────────────────────────────────────
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

    # ── 4. Handle BLOCKED ──────────────────────────────────────────────
    if not decision.approved:
        # DUPLICATE_REQUEST is a special case — the original PaymentRequest
        # already exists with that request_id, so we only write an audit log.
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

    # ── 5. Execute (agent is guaranteed non-None by policy check #1) ───
    assert agent is not None, "policy should have rejected missing agent"
    transaction = await execute(
        session=session,
        agent=agent,
        request_id=body.request_id,
        merchant_id=body.merchant_id,
        amount=body.amount,
    )

    # ── 6. Compute remaining daily limit ───────────────────────────────
    spent_today = await get_daily_spend(session, agent.id)
    remaining = max(0.0, agent.daily_limit - spent_today)

    return PaymentResponse(
        request_id=body.request_id,
        status="SETTLED",
        amount=body.amount,
        balance_after=agent.balance,
        remaining_daily_limit=remaining,
    )


# =============================================================================
# Helpers
# =============================================================================

async def _record_duplicate_blocked(
    session: AsyncSession,
    body: PaymentRequestSchema,
) -> None:
    """Log a duplicate-request block (no new PaymentRequest — already exists)."""
    import json

    from app.core.constants import AuditEventType
    from app.models.audit_log import AuditLog

    audit = AuditLog(
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
    session.add(audit)
    await session.commit()
    logger.info("Duplicate payment blocked: request=%s", body.request_id)


async def _record_blocked(
    session: AsyncSession,
    body: PaymentRequestSchema,
    reason: str,
) -> None:
    """Persist a BLOCKED PaymentRequest + AuditLog (fire-and-forget).

    If a PaymentRequest with the same request_id already exists
    (e.g. from a prior settlement), we skip the insert to avoid a
    UNIQUE constraint violation.
    """
    import json

    from sqlalchemy import select

    from app.core.constants import AuditEventType
    from app.models.audit_log import AuditLog
    from app.models.payment_request import PaymentRequest

    # Check if this request_id already exists
    result = await session.execute(
        select(PaymentRequest).where(PaymentRequest.request_id == body.request_id)
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        pr = PaymentRequest(
            request_id=body.request_id,
            agent_id=body.agent_id,
            merchant_id=body.merchant_id,
            amount=body.amount,
            status="BLOCKED",
            reason=reason,
        )
        session.add(pr)

    audit = AuditLog(
        actor=f"agent:{body.agent_id}",
        event_type=AuditEventType.PAYMENT_BLOCKED.value,
        details=json.dumps({
            "request_id": body.request_id,
            "agent_id": body.agent_id,
            "merchant_id": body.merchant_id,
            "amount": body.amount,
            "reason": reason,
        }),
    )
    session.add(audit)
    await session.commit()
    logger.info(
        "Payment BLOCKED: request=%s reason=%s", body.request_id, reason,
    )
