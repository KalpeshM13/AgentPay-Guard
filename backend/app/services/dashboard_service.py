"""Dashboard service — read-only aggregation queries for the owner UI using Firestore.

All functions accept a Firebase client and return dictionaries or
lists ready for Pydantic serialisation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.core.constants import AgentStatus

logger = logging.getLogger(__name__)


# =============================================================================
# GET /dashboard/summary
# =============================================================================

async def get_summary(session: any) -> dict:
    """Return the KPIs the owner dashboard needs."""
    today = _today_start()

    # -- Agent counts & balance ----------------------------------------------
    agents = await session.query("agents")
    total_agents = len(agents)
    frozen_agents = sum(1 for a in agents if a.get("status") == AgentStatus.FROZEN.value)
    active_agents = total_agents - frozen_agents
    total_balance = sum(float(a.get("balance", 0.0)) for a in agents)

    # -- Today's spending (only settled transactions) ------------------------
    # Since Firestore query filter combinations are restricted without composite indexes,
    # we can fetch all transactions from today and filter/aggregate locally.
    transactions = await session.query("transactions", [("settled_at", ">=", today)])
    today_spending = sum(float(tx.get("amount", 0.0)) for tx in transactions)

    # -- Today's request counts ----------------------------------------------
    requests_today = await session.query("payment_requests", [("created_at", ">=", today)])
    today_settled = sum(1 for pr in requests_today if pr.get("status") == "SETTLED")
    today_blocked = sum(1 for pr in requests_today if pr.get("status") == "BLOCKED")

    return {
        "total_agents": total_agents,
        "frozen_agents": frozen_agents,
        "active_agents": active_agents,
        "total_balance": round(total_balance, 2),
        "today_spending": round(today_spending, 2),
        "today_settled_count": today_settled,
        "today_blocked_count": today_blocked,
    }


# =============================================================================
# GET /dashboard/activity
# =============================================================================

async def get_activity(
    session: any,
    *,
    agent_id: int | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Return recent payment requests (SETTLED + BLOCKED), newest first."""
    filters = []
    if agent_id is not None:
        filters.append(("agent_id", "==", agent_id))
    if status_filter is not None:
        filters.append(("status", "==", status_filter))

    # Fetch matching payment requests ordered by created_at desc
    # In Firestore, sorting and filtering requires composite indexes unless it is simple.
    # To be safe and avoid composite index errors, we can query matching docs, sort locally, and apply limit.
    all_reqs = await session.query("payment_requests", filters=filters)
    
    # Sort locally by created_at desc
    def get_created_at(pr):
        ca = pr.get("created_at")
        if ca is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if hasattr(ca, "to_datetime"):
            return ca.to_datetime()
        if isinstance(ca, str):
            try:
                return datetime.fromisoformat(ca.replace("Z", "+00:00"))
            except ValueError:
                pass
        return ca
        
    all_reqs.sort(key=get_created_at, reverse=True)
    
    total = len(all_reqs)
    rows = all_reqs[:limit]

    # Resolve agent names in batch
    agent_ids = {r.get("agent_id") for r in rows if r.get("agent_id") is not None}
    agent_names: dict[int, str] = {}
    for a_id in agent_ids:
        agent_data = await session.get("agents", a_id)
        if agent_data:
            agent_names[a_id] = agent_data.get("name", f"Agent-{a_id}")

    items = []
    for r in rows:
        created_at_dt = get_created_at(r)
        items.append({
            "id": r.get("id"),
            "request_id": r.get("request_id"),
            "agent_id": r.get("agent_id"),
            "agent_name": agent_names.get(r.get("agent_id")),
            "merchant_id": r.get("merchant_id"),
            "amount": r.get("amount"),
            "status": r.get("status"),
            "reason": r.get("reason"),
            "timestamp": created_at_dt,
        })
        
    return items, total


# =============================================================================
# GET /dashboard/audit
# =============================================================================

async def get_audit(
    session: any,
    *,
    event_type: str | None = None,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Return recent audit-log entries, newest first."""
    filters = []
    if event_type is not None:
        filters.append(("event_type", "==", event_type))

    # Fetch matching audit events, sort locally to avoid index creation requirements
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
    
    total = len(all_audits)
    rows = all_audits[:limit]

    items = []
    for r in rows:
        ts_dt = get_timestamp(r)
        
        # Details in Firestore might be a dict or a serialized JSON string.
        details_val = r.get("details")
        if isinstance(details_val, str):
            try:
                # If it's a JSON string, try to parse it or keep it as is
                pass
            except Exception:
                pass

        items.append({
            "id": r.get("id"),
            "actor": r.get("actor"),
            "event_type": r.get("event_type"),
            "details": details_val,
            "timestamp": ts_dt,
        })
    return items, total


# =============================================================================
# Helpers
# =============================================================================

def _today_start() -> datetime:
    """Return the start of the current UTC day."""
    return datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
