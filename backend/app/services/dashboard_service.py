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


async def _get_admin_user_id(session: any) -> int:
    """Helper to retrieve the seeded admin's user ID dynamically."""
    from app.core.config import settings
    from app.services.auth_service import get_user_by_email
    email = settings.DEFAULT_OWNER_EMAIL.lower().strip()
    admin_user = await get_user_by_email(session, email)
    return admin_user.id if admin_user is not None else 1


# =============================================================================
# GET /dashboard/summary
# =============================================================================

async def get_summary(session: any, user_id: int | None = None) -> dict:
    """Return the KPIs the owner dashboard needs."""
    today = _today_start()
    admin_user_id = await _get_admin_user_id(session) if user_id is not None else 1

    # -- Agent counts & balance ----------------------------------------------
    agents = await session.query("agents")
    filtered_agents = []
    for a in agents:
        a_uid = a.get("user_id")
        if user_id is not None:
            if a_uid != user_id and not (user_id == admin_user_id and a_uid is None):
                continue
        filtered_agents.append(a)
        
    total_agents = len(filtered_agents)
    frozen_agents = sum(1 for a in filtered_agents if a.get("status") == AgentStatus.FROZEN.value)
    active_agents = total_agents - frozen_agents
    total_balance = sum(float(a.get("balance", 0.0)) for a in filtered_agents)

    # -- Today's spending (only settled transactions) ------------------------
    transactions = await session.query("transactions")
    today_spending = 0.0
    for tx in transactions:
        # filter user_id
        tx_uid = tx.get("user_id")
        if user_id is not None:
            if tx_uid != user_id and not (user_id == admin_user_id and tx_uid is None):
                continue
        # check settled_at >= today
        settled_at = tx.get("settled_at")
        if settled_at:
            if hasattr(settled_at, "to_datetime"):
                settled_at_dt = settled_at.to_datetime()
            elif isinstance(settled_at, str):
                settled_at_dt = datetime.fromisoformat(settled_at.replace("Z", "+00:00"))
            else:
                settled_at_dt = settled_at
            
            if settled_at_dt >= today:
                today_spending += float(tx.get("amount", 0.0))

    # -- Today's request counts ----------------------------------------------
    requests_today = await session.query("payment_requests")
    today_settled = 0
    today_blocked = 0
    for pr in requests_today:
        # filter user_id
        pr_uid = pr.get("user_id")
        if user_id is not None:
            if pr_uid != user_id and not (user_id == admin_user_id and pr_uid is None):
                continue
        # check today
        created_at = pr.get("created_at")
        if created_at:
            if hasattr(created_at, "to_datetime"):
                created_at_dt = created_at.to_datetime()
            elif isinstance(created_at, str):
                created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_at_dt = created_at
            
            if created_at_dt >= today:
                if pr.get("status") == "SETTLED":
                    today_settled += 1
                elif pr.get("status") == "BLOCKED":
                    today_blocked += 1

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
    user_id: int | None = None,
) -> tuple[list[dict], int]:
    """Return recent payment requests (SETTLED + BLOCKED), newest first."""
    all_reqs = await session.query("payment_requests")
    admin_user_id = await _get_admin_user_id(session) if user_id is not None else 1
    
    filtered_reqs = []
    for r in all_reqs:
        # Filter user_id
        r_uid = r.get("user_id")
        if user_id is not None:
            if r_uid != user_id and not (user_id == admin_user_id and r_uid is None):
                continue
        # Filter agent_id
        if agent_id is not None and r.get("agent_id") != agent_id:
            continue
        # Filter status
        if status_filter is not None and r.get("status") != status_filter:
            continue
        filtered_reqs.append(r)

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
        
    filtered_reqs.sort(key=get_created_at, reverse=True)
    
    total = len(filtered_reqs)
    rows = filtered_reqs[:limit]

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
    user_id: int | None = None,
) -> tuple[list[dict], int]:
    """Return recent audit-log entries, newest first."""
    all_audits = await session.query("audit_events")
    admin_user_id = await _get_admin_user_id(session) if user_id is not None else 1
    
    filtered_audits = []
    for r in all_audits:
        # Filter user_id
        r_uid = r.get("user_id")
        if user_id is not None:
            if r_uid != user_id and not (user_id == admin_user_id and r_uid is None):
                continue
        # Filter event_type
        if event_type is not None and r.get("event_type") != event_type:
            continue
        filtered_audits.append(r)
        
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
        
    filtered_audits.sort(key=get_timestamp, reverse=True)
    
    total = len(filtered_audits)
    rows = filtered_audits[:limit]

    items = []
    for r in rows:
        ts_dt = get_timestamp(r)
        details_val = r.get("details")

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
