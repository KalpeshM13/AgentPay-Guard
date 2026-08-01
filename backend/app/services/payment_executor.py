"""Payment Executor — the only component allowed to move money.

Design principle
----------------
The Executor **assumes policy approval has already been granted**.
It never re-checks policy rules.  Its sole job is to:

1.  Debit the agent's simulated wallet balance (within a DB transaction).
2.  Record a ``PaymentRequest`` (status = SETTLED).
3.  Record a ``Transaction`` with ``balance_before`` / ``balance_after``.
4.  Write an ``AuditLog`` entry.

Everything happens inside a single database transaction via
``session.begin()`` — if any step fails, the entire payment rolls back.

Independently testable
----------------------
The executor accepts any SQLAlchemy ``AsyncSession``, so tests can
use an in-memory SQLite database without starting the FastAPI server.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditEventType
from app.models.audit_log import AuditLog
from app.models.payment_request import PaymentRequest
from app.models.transaction import Transaction

if TYPE_CHECKING:
    from app.models.agent import Agent

logger = logging.getLogger(__name__)


# =============================================================================
# Public API
# =============================================================================


async def execute(
    *,
    session: AsyncSession,
    agent: Agent,
    request_id: str,
    merchant_id: int,
    amount: float,
) -> Transaction:
    """Execute an already-approved payment.

    **The caller must have verified policy approval before calling this.**

    Parameters
    ----------
    session : AsyncSession
        An active SQLAlchemy async session.  The executor opens a nested
        transaction inside it.
    agent : Agent
        The agent whose balance will be debited.  Must be an ORM instance
        attached to *session*.
    request_id : str
        The client-supplied idempotency key.
    merchant_id : int
        The merchant being paid.
    amount : float
        The amount to debit (must be > 0).

    Returns
    -------
    Transaction
        The newly created transaction record (with ``balance_before`` and
        ``balance_after`` populated).

    Raises
    ------
    ValueError
        If ``amount <= 0`` or ``agent.balance < amount`` (sanity guards;
        policy should have caught these already).
    """
    # -- Sanity guards (should never fire if policy ran first) ---------------
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if amount > agent.balance:
        raise ValueError(
            f"Insufficient balance: need {amount}, have {agent.balance}"
        )

    balance_before = agent.balance

    # -- 1. Debit the simulated wallet ---------------------------------------
    agent.balance -= amount
    session.add(agent)

    # -- 2. Create PaymentRequest (status = SETTLED) -------------------------
    payment_request = PaymentRequest(
        request_id=request_id,
        agent_id=agent.id,
        merchant_id=merchant_id,
        amount=amount,
        status="SETTLED",
        reason=None,
    )
    session.add(payment_request)

    # -- 3. Create Transaction (ledger entry) --------------------------------
    transaction = Transaction(
        request_id=request_id,
        agent_id=agent.id,
        amount=amount,
        balance_before=balance_before,
        balance_after=agent.balance,
    )
    session.add(transaction)

    # -- 4. Write AuditLog ---------------------------------------------------
    audit = AuditLog(
        actor=f"agent:{agent.id}",
        event_type=AuditEventType.PAYMENT_SETTLED.value,
        details=json.dumps({
            "request_id": request_id,
            "agent_id": agent.id,
            "merchant_id": merchant_id,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": agent.balance,
        }),
    )
    session.add(audit)

    # -- 5. Commit the transaction -------------------------------------------
    await session.commit()
    await session.refresh(transaction)

    logger.info(
        "Payment SETTLED: agent=%d merchant=%d amount=%.2f "
        "balance %.2f → %.2f request=%s tx_id=%d",
        agent.id, merchant_id, amount,
        balance_before, agent.balance,
        request_id, transaction.id,
    )

    return transaction


# =============================================================================
# Query helpers (used by the policy engine callbacks and dashboard)
# =============================================================================


async def get_daily_spend(session: AsyncSession, agent_id: int) -> float:
    """Return the total SETTLED spend for *agent_id* on the current UTC day.

    Used as the ``get_daily_spend`` callback in ``PolicyContext``.
    """
    from sqlalchemy import func, select

    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0))
        .where(
            Transaction.agent_id == agent_id,
            Transaction.settled_at >= today,
        )
    )
    return float(result.scalar_one())


async def count_recent_requests(
    session: AsyncSession, agent_id: int, window_start: datetime,
) -> int:
    """Count payment requests since *window_start*.

    Used as the ``count_recent_requests`` callback in ``PolicyContext``.
    """
    from sqlalchemy import func, select

    result = await session.execute(
        select(func.count(PaymentRequest.id))
        .where(
            PaymentRequest.agent_id == agent_id,
            PaymentRequest.created_at >= window_start,
        )
    )
    return result.scalar_one()


async def is_duplicate_request_id(
    session: AsyncSession, request_id: str,
) -> bool:
    """Check whether *request_id* has already been used.

    Used as the ``is_duplicate_request_id`` callback in ``PolicyContext``.
    """
    from sqlalchemy import exists, select

    result = await session.execute(
        select(exists().where(PaymentRequest.request_id == request_id))
    )
    return bool(result.scalar_one())
