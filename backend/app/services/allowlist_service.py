"""Allowlist business logic — manage which merchants an agent can pay.

All database access goes through this module.
"""

import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.agent_merchant import AgentMerchant
from app.models.merchant import Merchant

logger = logging.getLogger(__name__)


# =============================================================================
# Queries
# =============================================================================

async def list_allowlist(
    session: AsyncSession, agent: Agent,
) -> list[AgentMerchant]:
    """Return all allowlist entries for *agent*, with the merchant eagerly loaded."""
    result = await session.execute(
        select(AgentMerchant)
        .where(AgentMerchant.agent_id == agent.id)
        .options(selectinload(AgentMerchant.merchant))
        .order_by(AgentMerchant.id)
    )
    return list(result.scalars().all())


async def get_allowlist_entry(
    session: AsyncSession, agent_id: int, merchant_id: int,
) -> AgentMerchant | None:
    """Check whether a specific agent→merchant allowlist entry exists."""
    result = await session.execute(
        select(AgentMerchant)
        .where(
            AgentMerchant.agent_id == agent_id,
            AgentMerchant.merchant_id == merchant_id,
        )
    )
    return result.scalar_one_or_none()


# =============================================================================
# Mutations
# =============================================================================

async def add_to_allowlist(
    session: AsyncSession, agent: Agent, merchant: Merchant,
) -> AgentMerchant:
    """Add *merchant* to *agent*'s allowlist.

    Raises ``ValueError`` if the entry already exists.
    """
    entry = AgentMerchant(agent_id=agent.id, merchant_id=merchant.id)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    # Reload with merchant relationship
    result = await session.execute(
        select(AgentMerchant)
        .where(AgentMerchant.id == entry.id)
        .options(selectinload(AgentMerchant.merchant))
    )
    entry = result.scalar_one()
    logger.info(
        "Allowlist: agent %d (%s) now allowed to pay merchant %d (%s)",
        agent.id, agent.name, merchant.id, merchant.display_name,
    )
    return entry


async def remove_from_allowlist(
    session: AsyncSession, entry: AgentMerchant,
) -> None:
    """Remove a specific allowlist entry."""
    agent_id = entry.agent_id
    merchant_id = entry.merchant_id
    await session.delete(entry)
    await session.commit()
    logger.info(
        "Allowlist: removed agent %d → merchant %d", agent_id, merchant_id,
    )
