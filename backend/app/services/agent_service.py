"""Agent business logic — create, read, update, delete, freeze/unfreeze.

All database access goes through this module.  Routers only call these
functions and return the result.
"""

import json
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import AgentStatus, AuditEventType
from app.models.agent import Agent
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


# =============================================================================
# Queries
# =============================================================================

async def get_agent_by_id(
    session: AsyncSession, agent_id: int, *, load_allowlist: bool = True,
) -> Agent | None:
    """Fetch a single agent by PK.  Eager-loads allowlist entries and merchants."""
    from app.models.agent_merchant import AgentMerchant
    stmt = select(Agent).where(Agent.id == agent_id)
    stmt = stmt.options(
        selectinload(Agent.allowlist_entries).selectinload(AgentMerchant.merchant)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_agent_by_name(session: AsyncSession, name: str) -> Agent | None:
    """Fetch an agent by its unique name."""
    result = await session.execute(select(Agent).where(Agent.name == name))
    return result.scalar_one_or_none()


async def get_agent_by_identifier(
    session: AsyncSession, identifier: str | int
) -> Agent | None:
    """Fetch a single agent by PK (if integer-like) or by name (case-insensitively, with normalization)."""
    from app.models.agent_merchant import AgentMerchant
    
    try:
        agent_id = int(identifier)
        stmt = select(Agent).where(Agent.id == agent_id)
    except ValueError:
        name_str = str(identifier).strip()
        normalized_1 = name_str.lower()
        normalized_2 = name_str.lower().replace("_", "-")
        normalized_3 = name_str.lower().replace("-", "_")
        
        stmt = select(Agent).where(
            (func.lower(Agent.name) == normalized_1) |
            (func.lower(Agent.name) == normalized_2) |
            (func.lower(Agent.name) == normalized_3)
        )

    stmt = stmt.options(
        selectinload(Agent.allowlist_entries).selectinload(AgentMerchant.merchant)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()



async def list_agents(
    session: AsyncSession,
    *,
    status: AgentStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Agent], int]:
    """Return a page of agents with an optional status filter, ordered by id."""
    from app.models.agent_merchant import AgentMerchant
    stmt = select(Agent)
    count_stmt = select(func.count(Agent.id))

    if status is not None:
        stmt = stmt.where(Agent.status == status)
        count_stmt = count_stmt.where(Agent.status == status)

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Agent.id).offset(skip).limit(limit)
    stmt = stmt.options(
        selectinload(Agent.allowlist_entries).selectinload(AgentMerchant.merchant)
    )
    agents = (await session.execute(stmt)).scalars().all()
    return list(agents), total


# =============================================================================
# Mutations
# =============================================================================

async def create_agent(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    balance: float,
    per_transaction_limit: float,
    daily_limit: float,
    max_requests_per_minute: int,
) -> Agent:
    """Create a new agent and persist it."""
    agent = Agent(
        name=name.strip(),
        description=description.strip() if description else None,
        status=AgentStatus.ACTIVE,
        balance=balance,
        per_transaction_limit=per_transaction_limit,
        daily_limit=daily_limit,
        max_requests_per_minute=max_requests_per_minute,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    _write_audit(
        session, actor="system", event_type=AuditEventType.AGENT_CREATED,
        details={
            "agent_id": agent.id, "name": agent.name,
            "balance": agent.balance,
            "per_transaction_limit": agent.per_transaction_limit,
            "daily_limit": agent.daily_limit,
        },
    )
    await session.commit()

    logger.info(
        "Agent created: id=%d name=%s balance=%.2f per_tx=%.2f daily=%.2f",
        agent.id, agent.name, agent.balance,
        agent.per_transaction_limit, agent.daily_limit,
    )
    return agent


async def update_agent(
    session: AsyncSession,
    agent: Agent,
    *,
    name: str | None = None,
    description: str | None = None,
    balance: float | None = None,
    per_transaction_limit: float | None = None,
    daily_limit: float | None = None,
    max_requests_per_minute: int | None = None,
) -> Agent:
    """Partially update an agent's fields.  Only non-None values are applied."""
    changed = []
    policy_changed = {}

    if name is not None:
        agent.name = name.strip()
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

    await session.commit()
    await session.refresh(agent)

    if policy_changed:
        _write_audit(
            session, actor="system", event_type=AuditEventType.POLICY_UPDATED,
            details={
                "agent_id": agent.id, "agent_name": agent.name,
                "changes": policy_changed,
            },
        )
        await session.commit()

    logger.info("Agent %d updated: %s", agent.id, ", ".join(changed))
    return agent


async def delete_agent(session: AsyncSession, agent: Agent) -> None:
    """Delete an agent (and cascade to allowlist entries)."""
    agent_id = agent.id
    agent_name = agent.name
    await session.delete(agent)
    await session.commit()
    logger.info("Agent deleted: id=%d name=%s", agent_id, agent_name)


async def freeze_agent(session: AsyncSession, agent: Agent) -> Agent:
    """Set agent status to FROZEN — all future payment requests are blocked."""
    agent.status = AgentStatus.FROZEN
    await session.commit()
    await session.refresh(agent)

    _write_audit(
        session, actor="system", event_type=AuditEventType.AGENT_FROZEN,
        details={"agent_id": agent.id, "agent_name": agent.name},
    )
    await session.commit()

    logger.info("Agent %d FROZEN", agent.id)
    return agent


async def unfreeze_agent(session: AsyncSession, agent: Agent) -> Agent:
    """Set agent status back to ACTIVE."""
    agent.status = AgentStatus.ACTIVE
    await session.commit()
    await session.refresh(agent)

    _write_audit(
        session, actor="system", event_type=AuditEventType.AGENT_UNFROZEN,
        details={"agent_id": agent.id, "agent_name": agent.name},
    )
    await session.commit()

    logger.info("Agent %d UNFROZEN", agent.id)
    return agent


# =============================================================================
# Helpers
# =============================================================================


def _write_audit(
    session: AsyncSession,
    *,
    actor: str,
    event_type: AuditEventType,
    details: dict,
) -> None:
    """Append an audit-log entry (fire-and-forget; caller flushes)."""
    audit = AuditLog(
        actor=actor,
        event_type=event_type.value,
        details=json.dumps(details),
    )
    session.add(audit)
