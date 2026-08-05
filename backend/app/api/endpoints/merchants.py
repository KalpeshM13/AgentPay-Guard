"""Merchant CRUD endpoints.

**All mutations require ``admin`` or ``owner``.**  Reads are available to
any authenticated user.

Every endpoint delegates to ``merchant_service`` — no business logic here.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.crud_schemas import (
    MerchantCreate,
    MerchantListResponse,
    MerchantResponse,
)
from app.db.session import get_session
from app.services import merchant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchants", tags=["merchants"])



@router.post(
    "",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new merchant",
    description="**Requires ``admin`` or ``owner``.**",
    responses={
        201: {"description": "Merchant created."},
        409: {"description": "Merchant name already taken."},
    },
)
async def create(
    body: MerchantCreate,
    session = Depends(get_session),
) -> MerchantResponse:
    """Create a merchant."""
    existing = await merchant_service.get_merchant_by_name(session, body.display_name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Merchant '{body.display_name}' already exists.",
        )
    merchant = await merchant_service.create_merchant(
        session,
        display_name=body.display_name,
        destination_reference=body.destination_reference,
        description=body.description,
    )
    return MerchantResponse.model_validate(merchant)



@router.get(
    "",
    response_model=MerchantListResponse,
    summary="List all merchants",
    description="Paginated list, newest first.",
)
async def list_all(
    active_only: bool = Query(
        default=False,
        description="When true, only returns active merchants.",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    session = Depends(get_session),
) -> MerchantListResponse:
    """List merchants."""
    merchants, total = await merchant_service.list_merchants(
        session, active_only=active_only, skip=skip, limit=limit,
    )
    return MerchantListResponse(
        total=total,
        merchants=[MerchantResponse.model_validate(m) for m in merchants],
    )



@router.delete(
    "/{merchant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a merchant",
    description="Permanently deletes the merchant and cascading allowlist entries.  **Requires ``admin`` or ``owner``.**",
    responses={
        204: {"description": "Merchant deleted."},
        404: {"description": "Merchant not found."},
    },
)
async def delete_one(
    merchant_id: int,
    session = Depends(get_session),
) -> None:
    """Delete a merchant."""
    merchant = await merchant_service.get_merchant_by_id(session, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")
    await merchant_service.delete_merchant(session, merchant)
