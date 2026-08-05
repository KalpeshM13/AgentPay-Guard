"""Agent business logic — create, read, update, delete, freeze/unfreeze using Firestore.

All database access goes through this module.
"""

import json
import logging
from datetime import datetime, timezone

from app.core.constants import AgentStatus, AuditEventType
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.agent_merchant import AgentMerchant
from app.models.merchant import Merchant

logger = logging.getLogger(__name__)



async def _load_agent_relations(session: any, agent: Agent) -> None:
    """Fetch and attach allowlist entries and merchants for an agent."""
    entries_data = await session.query("agent_allowlist", [("agent_id", "==", agent.id)])
    allowlist_entries = []
    for ed in entries_data:
        entry = AgentMerchant(**ed)
        m_data = await session.get("merchants", entry.merchant_id)
        if m_data:
            entry.merchant = Merchant(**m_data)
        else:
            entry.merchant = None
        allowlist_entries.append(entry)
    agent.allowlist_entries = allowlist_entries



async def get_agent_by_id(
    session: any, agent_id: int, *, load_allowlist: bool = True,
) -> Agent | None:
    """Fetch a single agent by PK. Eager-loads allowlist entries and merchants."""
    data = await session.get("agents", agent_id)
    if not data:
        return None
    agent = Agent(**data)
    if load_allowlist:
        await _load_agent_relations(session, agent)
    return agent


async def get_agent_by_name(session: any, name: str) -> Agent | None:
    """Fetch an agent by its unique name."""
    name_lower = name.strip().lower()
    results = await session.query("agents", [("name_lower", "==", name_lower)])
    if results:
        agent = Agent(**results[0])
        await _load_agent_relations(session, agent)
        return agent
    return None


async def get_agent_by_identifier(
    session: any, identifier: str | int
) -> Agent | None:
    """Fetch a single agent by PK (if integer-like) or by name (case-insensitively)."""
    try:
        agent_id = int(identifier)
        agent = await get_agent_by_id(session, agent_id)
        if agent:
            return agent
        return None
    except ValueError:
        name_str = str(identifier).strip().lower()
        for n_str in [name_str, name_str.replace("_", "-"), name_str.replace("-", "_")]:
            results = await session.query("agents", [("name_lower", "==", n_str)])
            if results:
                agent = Agent(**results[0])
                await _load_agent_relations(session, agent)
                return agent
        return None


async def list_agents(
    session: any,
    *,
    status: AgentStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Agent], int]:
    """Return a page of agents with an optional status filter, ordered by id."""
    all_matching = await session.query("agents")
    
    filtered = []
    for data in all_matching:
        if status is not None:
            a_status = data.get("status")
            status_val = status.value if isinstance(status, AgentStatus) else status
            if a_status != status_val:
                continue
        
        filtered.append(Agent(**data))
        
    filtered.sort(key=lambda x: x.id)
    
    total = len(filtered)
    matching_page = filtered[skip : skip + limit]
    
    agents = []
    for agent in matching_page:
        await _load_agent_relations(session, agent)
        agents.append(agent)
        
    return agents, total



async def create_agent(
    session: any,
    *,
    name: str,
    description: str | None,
    balance: float,
    per_transaction_limit: float,
    daily_limit: float,
    max_requests_per_minute: int,
) -> Agent:
    """Create a new agent and persist it in Firestore."""
    next_id = await session.get_next_id("agents")
    agent = Agent(
        id=next_id,
        name=name.strip(),
        name_lower=name.strip().lower(),
        description=description.strip() if description else None,
        status=AgentStatus.ACTIVE,
        balance=balance,
        per_transaction_limit=per_transaction_limit,
        daily_limit=daily_limit,
        max_requests_per_minute=max_requests_per_minute,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await session.insert("agents", next_id, agent.to_dict())

    await _write_audit(
        session, actor="system", event_type=AuditEventType.AGENT_CREATED,
        details={
            "agent_id": agent.id, "name": agent.name,
            "balance": agent.balance,
            "per_transaction_limit": agent.per_transaction_limit,
            "daily_limit": agent.daily_limit,
        },
    )

    logger.info(
        "Agent created: id=%d name=%s balance=%.2f per_tx=%.2f daily=%.2f",
        agent.id, agent.name, agent.balance,
        agent.per_transaction_limit, agent.daily_limit,
    )
    return agent


async def update_agent(
    session: any,
    agent: Agent,
    *,
    name: str | None = None,
    description: str | None = None,
    balance: float | None = None,
    per_transaction_limit: float | None = None,
    daily_limit: float | None = None,
    max_requests_per_minute: int | None = None,
) -> Agent:
    """Partially update an agent's fields. Only non-None values are applied."""
    changed = []
    policy_changed = {}

    if name is not None:
        agent.name = name.strip()
        agent.name_lower = name.strip().lower()
        changed.append("name")
    if description is not None:
        agent.description = description.strip() or None
        changed.append("description")
    if balance is not None:
        agent.balance = balance
        changed.append("balance")
    if per_transaction_limit is not None:
        old = agent.per_transaction_limit
        agent.per_transaction_limit = per_transaction_limit
        changed.append("per_transaction_limit")
        policy_changed["per_transaction_limit"] = {"old": old, "new": per_transaction_limit}
    if daily_limit is not None:
        old = agent.daily_limit
        agent.daily_limit = daily_limit
        changed.append("daily_limit")
        policy_changed["daily_limit"] = {"old": old, "new": daily_limit}
    if max_requests_per_minute is not None:
        old = agent.max_requests_per_minute
        agent.max_requests_per_minute = max_requests_per_minute
        changed.append("max_requests_per_minute")
        policy_changed["max_requests_per_minute"] = {"old": old, "new": max_requests_per_minute}

    if not changed:
        return agent

    agent.updated_at = datetime.now(timezone.utc)
    await session.update("agents", agent.id, agent.to_dict())

    if policy_changed:
        await _write_audit(
            session, actor="system", event_type=AuditEventType.POLICY_UPDATED,
            details={
                "agent_id": agent.id, "agent_name": agent.name,
                "changes": policy_changed,
            },
        )

    logger.info("Agent %d updated in Firestore: %s", agent.id, ", ".join(changed))
    return agent


async def delete_agent(session: any, agent: Agent) -> None:
    """Delete an agent (and cascade to allowlist entries in Firestore)."""
    agent_id = agent.id
    agent_name = agent.name
    
    entries_data = await session.query("agent_allowlist", [("agent_id", "==", agent_id)])
    for ed in entries_data:
        await session.delete("agent_allowlist", ed["id"])
        
    await session.delete("agents", agent_id)
    logger.info("Agent deleted: id=%d name=%s", agent_id, agent_name)


async def freeze_agent(session: any, agent: Agent) -> Agent:
    """Set agent status to FROZEN — all future payment requests are blocked."""
    agent.status = AgentStatus.FROZEN
    agent.updated_at = datetime.now(timezone.utc)
    await session.update("agents", agent.id, agent.to_dict())

    await _write_audit(
        session, actor="system", event_type=AuditEventType.AGENT_FROZEN,
        details={"agent_id": agent.id, "agent_name": agent.name},
    )

    logger.info("Agent %d FROZEN", agent.id)
    return agent


async def unfreeze_agent(session: any, agent: Agent) -> Agent:
    """Set agent status back to ACTIVE."""
    agent.status = AgentStatus.ACTIVE
    agent.updated_at = datetime.now(timezone.utc)
    await session.update("agents", agent.id, agent.to_dict())

    await _write_audit(
        session, actor="system", event_type=AuditEventType.AGENT_UNFROZEN,
        details={"agent_id": agent.id, "agent_name": agent.name},
    )

    logger.info("Agent %d UNFROZEN", agent.id)
    return agent



async def _write_audit(
    session: any,
    *,
    actor: str,
    event_type: AuditEventType,
    details: dict,
) -> None:
    """Append an audit-log entry to Firestore."""
    next_id = await session.get_next_id("audit_events")
    audit = AuditLog(
        id=next_id,
        actor=actor,
        event_type=event_type.value,
        details=json.dumps(details),
        timestamp=datetime.now(timezone.utc),
    )
    await session.insert("audit_events", next_id, audit.to_dict())
