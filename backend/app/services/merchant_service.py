"""Merchant business logic — create, read, delete counterparties using Firestore.

All database access goes through this module.
"""

import logging
from datetime import datetime, timezone

from app.models.merchant import Merchant

logger = logging.getLogger(__name__)


# =============================================================================
# Queries
# =============================================================================

async def get_merchant_by_id(
    session: any, merchant_id: int,
) -> Merchant | None:
    """Fetch a merchant by PK."""
    data = await session.get("merchants", merchant_id)
    if data:
        return Merchant(**data)
    return None


async def get_merchant_by_name(
    session: any, display_name: str,
) -> Merchant | None:
    """Fetch a merchant by its unique display name (case-insensitive)."""
    name_lower = display_name.strip().lower()
    results = await session.query("merchants", [("display_name_lower", "==", name_lower)])
    if results:
        return Merchant(**results[0])
    return None


async def list_merchants(
    session: any, *, active_only: bool = False,
    skip: int = 0, limit: int = 100,
) -> tuple[list[Merchant], int]:
    """Return a page of merchants, ordered by id."""
    filters = []
    if active_only:
        filters.append(("active", "==", True))

    all_matching = await session.query("merchants", filters=filters)
    total = len(all_matching)

    matching_page = await session.query("merchants", filters=filters, order_by="id", limit=limit, offset=skip)
    merchants = [Merchant(**data) for data in matching_page]

    return merchants, total


# =============================================================================
# Mutations
# =============================================================================

async def create_merchant(
    session: any,
    *,
    display_name: str,
    destination_reference: str,
    description: str | None = None,
) -> Merchant:
    """Create a new merchant in Firestore."""
    next_id = await session.get_next_id("merchants")
    merchant = Merchant(
        id=next_id,
        display_name=display_name.strip(),
        display_name_lower=display_name.strip().lower(),
        destination_reference=destination_reference.strip(),
        description=description.strip() if description else None,
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await session.insert("merchants", next_id, merchant.to_dict())
    logger.info(
        "Merchant created in Firestore: id=%d name=%s ref=%s",
        merchant.id, merchant.display_name, merchant.destination_reference,
    )
    return merchant


async def delete_merchant(session: any, merchant: Merchant) -> None:
    """Delete a merchant (cascades to allowlist entries in Firestore)."""
    mid = merchant.id
    mname = merchant.display_name
    
    # Cascade delete allowlist entries
    entries_data = await session.query("agent_allowlist", [("merchant_id", "==", mid)])
    for ed in entries_data:
        await session.delete("agent_allowlist", ed["id"])
        
    await session.delete("merchants", mid)
    logger.info("Merchant deleted from Firestore: id=%d name=%s", mid, mname)
