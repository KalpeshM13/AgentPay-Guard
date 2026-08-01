"""Database initialization — create tables and seed a default owner.

Called once at application startup (see ``app/main.py`` lifespan).
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import UserRole
from app.db.session import AsyncSessionLocal, Base, engine
from app.models import User  # noqa: F401 — ensure all models are loaded
from app.services.auth_service import get_user_by_email, hash_password

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables (if missing) and seed the default owner account.

    Safe to call repeatedly — the owner seed is idempotent.
    """

    # -- 1. Create tables ----------------------------------------------------
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not already present).")

    # -- 2. Seed default owner, agent and merchants --------------------------
    async with AsyncSessionLocal() as session:
        await _seed_default_owner(session)
        await _seed_default_agent_and_merchants(session)
        await session.commit()

    logger.info("Database initialization complete.")


async def _seed_default_owner(session: AsyncSession) -> None:
    """Create the default owner account if it does not already exist."""

    email = settings.DEFAULT_OWNER_EMAIL.lower().strip()
    existing = await get_user_by_email(session, email)

    if existing is not None:
        logger.debug("Default owner already exists (id=%d).", existing.id)
        return

    from app.models.user import User

    user = User(
        email=email,
        hashed_password=hash_password(settings.DEFAULT_OWNER_PASSWORD),
        display_name="Default Owner",
        role=UserRole.OWNER,
        is_active=True,
    )
    session.add(user)
    logger.info(
        "Seeded default owner: email=%s role=%s (change password immediately!).",
        email,
        UserRole.OWNER,
    )


async def _seed_default_agent_and_merchants(session: AsyncSession) -> None:
    """Seed the default merchants, default agent, and establish allowlist links."""
    from app.models.agent import Agent
    from app.models.merchant import Merchant
    from app.models.agent_merchant import AgentMerchant
    from app.core.constants import AgentStatus

    # 1. Seed merchants
    merchants_to_seed = [
        (1, "Compute Provider", "compute_provider", "Primary cloud compute vendor."),
        (2, "API Provider", "api_provider", "LLM API credits provider."),
        (3, "Vendor A", "vendor_a", "General tech supplier."),
        (4, "AWS Cloud Services", "aws_demo", "AWS cloud services account."),
        (5, "Malicious Recipient", "malicious_hacker", "Non-allowlisted malicious actor."),
    ]
    
    seeded_merchants = []
    for mid, name, ref, desc in merchants_to_seed:
        merchant = await session.get(Merchant, mid)
        if merchant is None:
            merchant = Merchant(
                id=mid,
                display_name=name,
                destination_reference=ref,
                description=desc,
                active=True,
            )
            session.add(merchant)
            logger.info("Seeded merchant: id=%d name=%s", mid, name)
        seeded_merchants.append(merchant)
    
    # 2. Seed agent
    agent = await session.get(Agent, 1)
    if agent is None:
        agent = Agent(
            id=1,
            name="Agent-01",
            description="Default autonomous spending agent",
            status=AgentStatus.ACTIVE,
            balance=10.0,
            per_transaction_limit=1.0,
            daily_limit=5.0,
            max_requests_per_minute=10,
        )
        session.add(agent)
        logger.info("Seeded default agent: id=1 name=%s", agent.name)
    
    # Flush so generated identities resolve
    await session.flush()

    # 3. Associate all 4 merchants to the agent's allowlist
    from sqlalchemy import select
    for merchant in seeded_merchants:
        if merchant.id == 5:
            continue
        stmt = select(AgentMerchant).where(
            AgentMerchant.agent_id == 1,
            AgentMerchant.merchant_id == merchant.id
        )
        existing_link = (await session.execute(stmt)).scalar_one_or_none()
        if existing_link is None:
            link = AgentMerchant(
                agent_id=1,
                merchant_id=merchant.id
            )
            session.add(link)
            logger.info("Added merchant %s to agent's allowlist", merchant.display_name)

