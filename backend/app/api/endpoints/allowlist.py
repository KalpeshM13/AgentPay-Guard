"""Allowlist management endpoints — control which merchants an agent can pay.

Placed under ``/agents/{id}/allowlist`` as a natural sub-resource.

**All mutations require ``admin`` or ``owner``.**  Reads require any
authenticated user.

Every endpoint delegates to ``allowlist_service`` — no business logic here.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import RequireAdmin, get_current_user
from app.api.crud_schemas import (
    AllowlistAdd,
    AllowlistEntryResponse,
    AllowlistResponse,
)
from app.db.session import get_session
from app.models.user import User
from app.services import agent_service, allowlist_service, merchant_service

logger = logging.getLogger(__name__)

# NOTE: the parent router registers this with prefix="/agents/{agent_id}/allowlist"
# so all routes here are relative to that prefix.
router = APIRouter(tags=["allowlist"])


# =============================================================================
# GET /agents/{agent_id}/allowlist
# =============================================================================

@router.get(
    "",
    response_model=AllowlistResponse,
    summary="Get an agent's allowlist",
    description="Returns all merchants this agent is allowed to pay.",
    responses={404: {"description": "Agent not found."}},
)
async def list_entries(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AllowlistResponse:
    """List allowlist entries for an agent."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    entries = await allowlist_service.list_allowlist(session, agent)
    return AllowlistResponse(
        agent_id=agent.id,
        total=len(entries),
        allowlist=[
            AllowlistEntryResponse(
                id=e.id,
                agent_id=e.agent_id,
                merchant_id=e.merchant_id,
                merchant_name=e.merchant.display_name,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


# =============================================================================
# POST /agents/{agent_id}/allowlist
# =============================================================================

@router.post(
    "",
    response_model=AllowlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a merchant to an agent's allowlist",
    description="**Requires ``admin`` or ``owner``.**",
    responses={
        201: {"description": "Merchant added to allowlist."},
        404: {"description": "Agent or merchant not found."},
        409: {"description": "Merchant already on the allowlist."},
    },
)
async def add_entry(
    agent_id: str,
    body: AllowlistAdd,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> AllowlistEntryResponse:
    """Add a merchant to an agent's allowlist."""
    # Validate agent exists
    agent = await agent_service.get_agent_by_identifier(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    # Validate merchant exists
    merchant = await merchant_service.get_merchant_by_id(session, body.merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")

    # Check it's not already on the list
    existing = await allowlist_service.get_allowlist_entry(
        session, agent.id, body.merchant_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Merchant '{merchant.display_name}' is already on this agent's allowlist.",
        )

    entry = await allowlist_service.add_to_allowlist(session, agent, merchant)
    return AllowlistEntryResponse(
        id=entry.id,
        agent_id=entry.agent_id,
        merchant_id=entry.merchant_id,
        merchant_name=entry.merchant.display_name,
        created_at=entry.created_at,
    )


# =============================================================================
# DELETE /agents/{agent_id}/allowlist/{merchant_id}
# =============================================================================

@router.delete(
    "/{merchant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a merchant from an agent's allowlist",
    description="**Requires ``admin`` or ``owner``.**",
    responses={
        204: {"description": "Entry removed."},
        404: {"description": "Allowlist entry not found."},
    },
)
async def remove_entry(
    agent_id: str,
    merchant_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> None:
    """Remove a merchant from an agent's allowlist."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
        
    entry = await allowlist_service.get_allowlist_entry(session, agent.id, merchant_id)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allowlist entry not found.",
        )
    await allowlist_service.remove_from_allowlist(session, entry)
