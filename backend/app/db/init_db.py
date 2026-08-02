"""Database initialization for Firestore — seed default owner, agents, and merchants.

Called once at application startup (see ``app/main.py`` lifespan).
"""

import logging

from app.core.config import settings
from app.db.session import FirebaseClient

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Seed the default owner account, agents and merchants to Firestore.

    Safe to call repeatedly — the seed is idempotent.
    """
    session = FirebaseClient()
    if session.db is None:
        logger.warning("Firebase not initialized. Seeding skipped.")
        return

    # Seed default data
    await _seed_default_agent_and_merchants(session)
    logger.info("Database initialization complete.")





async def _seed_default_agent_and_merchants(session: FirebaseClient) -> None:
    """Seed the default merchants, default agent, and establish allowlist links."""
    from app.models.agent import Agent
    from app.models.merchant import Merchant
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
        merchant_data = await session.get("merchants", mid)
        if merchant_data is None:
            merchant = Merchant(
                id=mid,
                display_name=name,
                display_name_lower=name.lower(),
                destination_reference=ref,
                description=desc,
                active=True,
            )
            await session.insert("merchants", mid, merchant.to_dict())
            logger.info("Seeded merchant: id=%d name=%s", mid, name)
        else:
            merchant = Merchant(**merchant_data)
        seeded_merchants.append(merchant)
        
    # Ensure counters is set to at least 5 for merchants
    counter_ref = session.db.collection("counters").document("merchants")
    snapshot = counter_ref.get()
    if not snapshot.exists or snapshot.get("value") < 5:
        counter_ref.set({"value": 5})
    
    # 2. Seed agent
    agent_data = await session.get("agents", 1)
    
    from app.core.config import settings

    if agent_data is None:
        agent = Agent(
            id=1,
            name="Agent-01",
            name_lower="agent-01",
            description="Default autonomous spending agent",
            status=AgentStatus.ACTIVE,
            balance=10.0,
            per_transaction_limit=1.0,
            daily_limit=5.0,
            max_requests_per_minute=10,
        )
        await session.insert("agents", 1, agent.to_dict())
        logger.info("Seeded default agent: id=1 name=%s", agent.name)
    else:
        agent = Agent(**agent_data)
        
    # Ensure counters is set to at least 1 for agents
    counter_ref_agents = session.db.collection("counters").document("agents")
    snapshot_agents = counter_ref_agents.get()
    if not snapshot_agents.exists or snapshot_agents.get("value") < 1:
        counter_ref_agents.set({"value": 1})

    # 3. Associate all 4 merchants to the agent's allowlist
    for merchant in seeded_merchants:
        if merchant.id == 5:
            continue
        
        from app.services.allowlist_service import get_allowlist_entry
        existing_link = await get_allowlist_entry(session, 1, merchant.id)
        if existing_link is None:
            from app.services.allowlist_service import add_to_allowlist
            agent_obj = Agent(id=1, name="Agent-01")
            await add_to_allowlist(session, agent_obj, merchant)
            logger.info("Added merchant %s to agent's allowlist", merchant.display_name)
