"""Allowlist business logic — manage which merchants an agent can pay in Firestore.

All database access goes through this module.
"""

import logging
from datetime import datetime, timezone

from app.models.agent import Agent
from app.models.agent_merchant import AgentMerchant
from app.models.merchant import Merchant

logger = logging.getLogger(__name__)



async def list_allowlist(
    session: any, agent: Agent,
) -> list[AgentMerchant]:
    """Return all allowlist entries for *agent*, with the merchant eagerly loaded."""
    results = await session.query("agent_allowlist", [("agent_id", "==", agent.id)], order_by="id")
    
    allowlist_entries = []
    for data in results:
        entry = AgentMerchant(**data)
        m_data = await session.get("merchants", entry.merchant_id)
        if m_data:
            entry.merchant = Merchant(**m_data)
        else:
            entry.merchant = None
        allowlist_entries.append(entry)
        
    return allowlist_entries


async def get_allowlist_entry(
    session: any, agent_id: int, merchant_id: int,
) -> AgentMerchant | None:
    """Check whether a specific agent→merchant allowlist entry exists."""
    results = await session.query(
        "agent_allowlist",
        [("agent_id", "==", agent_id), ("merchant_id", "==", merchant_id)]
    )
    if results:
        return AgentMerchant(**results[0])
    return None



async def add_to_allowlist(
    session: any, agent: Agent, merchant: Merchant,
) -> AgentMerchant:
    """Add *merchant* to *agent*'s allowlist in Firestore.

    Raises ``ValueError`` if the entry already exists.
    """
    existing = await get_allowlist_entry(session, agent.id, merchant.id)
    if existing is not None:
        raise ValueError("Allowlist entry already exists.")
        
    next_id = await session.get_next_id("agent_allowlist")
    entry = AgentMerchant(
        id=next_id,
        agent_id=agent.id,
        merchant_id=merchant.id,
        created_at=datetime.now(timezone.utc),
    )
    await session.insert("agent_allowlist", next_id, entry.to_dict())
    
    entry.merchant = merchant
    entry.agent = agent
    
    logger.info(
        "Allowlist: agent %d (%s) now allowed to pay merchant %d (%s)",
        agent.id, agent.name, merchant.id, merchant.display_name,
    )
    return entry


async def remove_from_allowlist(
    session: any, entry: AgentMerchant,
) -> None:
    """Remove a specific allowlist entry from Firestore."""
    agent_id = entry.agent_id
    merchant_id = entry.merchant_id
    await session.delete("agent_allowlist", entry.id)
    logger.info(
        "Allowlist: removed agent %d → merchant %d", agent_id, merchant_id,
    )
