"""Dashboard service — read-only aggregation queries for the owner UI.

All functions accept an ``AsyncSession`` and return dictionaries or
lists ready for Pydantic serialisation.  No mutations here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AgentStatus
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.payment_request import PaymentRequest
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


# =============================================================================
# GET /dashboard/summary
# =============================================================================


async def get_summary(session: AsyncSession) -> dict:
    """Return the KPIs the owner dashboard needs.

    Executes 4 lightweight queries in parallel fashion.
    """
    today = _today_start()

    # -- Agent counts --------------------------------------------------------
    total_agents = await session.scalar(
        select(func.count(Agent.id))
    )
    frozen_agents = await session.scalar(
        select(func.count(Agent.id)).where(Agent.status == AgentStatus.FROZEN)
    )
    active_agents = total_agents - frozen_agents

    # -- Total balance across all agents -------------------------------------
    total_balance = await session.scalar(
        select(func.coalesce(func.sum(Agent.balance), 0.0))
    )

    # -- Today's spending (only settled transactions) ------------------------
    today_spending = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0.0))
        .where(Transaction.settled_at >= today)
    )

    # -- Today's request counts ----------------------------------------------
    today_settled = await session.scalar(
        select(func.count(PaymentRequest.id))
        .where(PaymentRequest.created_at >= today, PaymentRequest.status == "SETTLED")
    )
    today_blocked = await session.scalar(
        select(func.count(PaymentRequest.id))
        .where(PaymentRequest.created_at >= today, PaymentRequest.status == "BLOCKED")
    )

    return {
        "total_agents": total_agents or 0,
        "frozen_agents": frozen_agents or 0,
        "active_agents": active_agents or 0,
        "total_balance": round(float(total_balance or 0.0), 2),
        "today_spending": round(float(today_spending or 0.0), 2),
        "today_settled_count": today_settled or 0,
        "today_blocked_count": today_blocked or 0,
    }


# =============================================================================
# GET /dashboard/activity
# =============================================================================


async def get_activity(
    session: AsyncSession,
    *,
    agent_id: int | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Return recent payment requests (SETTLED + BLOCKED), newest first.

    Optionally filters by ``agent_id`` and/or ``status``.
    """
    stmt = select(PaymentRequest)
    count_stmt = select(func.count(PaymentRequest.id))

    if agent_id is not None:
        stmt = stmt.where(PaymentRequest.agent_id == agent_id)
        count_stmt = count_stmt.where(PaymentRequest.agent_id == agent_id)
    if status_filter is not None:
        stmt = stmt.where(PaymentRequest.status == status_filter)
        count_stmt = count_stmt.where(PaymentRequest.status == status_filter)

    total = (await session.execute(count_stmt)).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(PaymentRequest.created_at.desc()).limit(limit)
        )
    ).scalars().all()

    # Resolve agent names in one batch
    agent_ids = {r.agent_id for r in rows if r.agent_id is not None}
    agent_names: dict[int, str] = {}
    if agent_ids:
        agents = (
            await session.execute(
                select(Agent.id, Agent.name).where(Agent.id.in_(agent_ids))
            )
        ).all()
        agent_names = {a.id: a.name for a in agents}

    items = [
        _payment_request_to_activity_item(r, agent_names.get(r.agent_id))
        for r in rows
    ]
    return items, total


# =============================================================================
# GET /dashboard/audit
# =============================================================================


async def get_audit(
    session: AsyncSession,
    *,
    event_type: str | None = None,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Return recent audit-log entries, newest first.

    Optionally filters by ``event_type``.
    """
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    if event_type is not None:
        stmt = stmt.where(AuditLog.event_type == event_type)
        count_stmt = count_stmt.where(AuditLog.event_type == event_type)

    total = (await session.execute(count_stmt)).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
        )
    ).scalars().all()

    items = [
        {
            "id": r.id,
            "actor": r.actor,
            "event_type": r.event_type,
            "details": r.details,
            "timestamp": r.timestamp,
        }
        for r in rows
    ]
    return items, total


# =============================================================================
# Helpers
# =============================================================================


def _today_start() -> datetime:
    """Return the start of the current UTC day."""
    return datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )


def _payment_request_to_activity_item(
    pr: PaymentRequest, agent_name: str | None,
) -> dict:
    """Map a PaymentRequest ORM row to the ActivityItem dict."""
    return {
        "id": pr.id,
        "request_id": pr.request_id,
        "agent_id": pr.agent_id,
        "agent_name": agent_name,
        "merchant_id": pr.merchant_id,
        "amount": pr.amount,
        "status": pr.status,
        "reason": pr.reason,
        "timestamp": pr.created_at,
    }
