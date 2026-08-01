"""Merchant business logic — create, read, delete counterparties.

All database access goes through this module.
"""

import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant

logger = logging.getLogger(__name__)


# =============================================================================
# Queries
# =============================================================================

async def get_merchant_by_id(
    session: AsyncSession, merchant_id: int,
) -> Merchant | None:
    """Fetch a merchant by PK."""
    result = await session.execute(
        select(Merchant).where(Merchant.id == merchant_id)
    )
    return result.scalar_one_or_none()


async def get_merchant_by_name(
    session: AsyncSession, display_name: str,
) -> Merchant | None:
    """Fetch a merchant by its unique display name."""
    result = await session.execute(
        select(Merchant).where(Merchant.display_name == display_name)
    )
    return result.scalar_one_or_none()


async def list_merchants(
    session: AsyncSession, *, active_only: bool = False,
    skip: int = 0, limit: int = 100,
) -> tuple[list[Merchant], int]:
    """Return a page of merchants, ordered by id."""

    stmt = select(Merchant)
    count_stmt = select(func.count(Merchant.id))

    if active_only:
        stmt = stmt.where(Merchant.active.is_(True))
        count_stmt = count_stmt.where(Merchant.active.is_(True))

    total = (await session.execute(count_stmt)).scalar_one()
    merchants = (
        await session.execute(stmt.order_by(Merchant.id).offset(skip).limit(limit))
    ).scalars().all()

    return list(merchants), total


# =============================================================================
# Mutations
# =============================================================================

async def create_merchant(
    session: AsyncSession,
    *,
    display_name: str,
    destination_reference: str,
    description: str | None = None,
) -> Merchant:
    """Create a new merchant."""
    merchant = Merchant(
        display_name=display_name.strip(),
        destination_reference=destination_reference.strip(),
        description=description.strip() if description else None,
        active=True,
    )
    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)
    logger.info(
        "Merchant created: id=%d name=%s ref=%s",
        merchant.id, merchant.display_name, merchant.destination_reference,
    )
    return merchant


async def delete_merchant(session: AsyncSession, merchant: Merchant) -> None:
    """Delete a merchant (cascades to allowlist entries)."""
    mid = merchant.id
    mname = merchant.display_name
    await session.delete(merchant)
    await session.commit()
    logger.info("Merchant deleted: id=%d name=%s", mid, mname)
