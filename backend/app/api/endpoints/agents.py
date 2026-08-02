"""Agent CRUD endpoints.

**All routes require authentication** (owner/admin for mutations, any
authenticated user for reads).  Each endpoint delegates to the
``agent_service`` layer — the router itself contains no business logic.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query


from app.api.auth_deps import RequireAdmin, get_current_user
from app.api.crud_schemas import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    PolicyUpdate,
)
from app.db.session import get_session
from app.models.user import User
from app.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


async def populate_agent_limits(session, agent) -> None:
    from app.services.payment_executor import get_daily_spend
    spent_today = await get_daily_spend(session, agent.id)
    agent.spent_today = spent_today
    agent.remaining_daily_limit = max(0.0, agent.daily_limit - spent_today)
    agent.per_tx_limit = agent.per_transaction_limit


# =============================================================================
# POST /agents
# =============================================================================

@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new autonomous agent",
    description="""
Creates a new AI agent with a simulated balance and spending limits.

**Requires:** ``admin`` or ``owner`` role.
""",
    responses={
        201: {"description": "Agent created."},
        409: {"description": "Agent name already taken."},
        422: {"description": "Validation error."},
    },
)
async def create(
    body: AgentCreate,
    session = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> AgentResponse:
    """Create an agent."""
    existing = await agent_service.get_agent_by_name(session, body.name, user_id=user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{body.name}' already exists.",
        )
    agent = await agent_service.create_agent(
        session,
        name=body.name,
        description=body.description,
        balance=body.balance,
        per_transaction_limit=body.per_transaction_limit,
        daily_limit=body.daily_limit,
        max_requests_per_minute=body.max_requests_per_minute,
        user_id=user.id,
    )
    await populate_agent_limits(session, agent)
    return AgentResponse.model_validate(agent)


# =============================================================================
# GET /agents
# =============================================================================

@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all agents",
    description="Returns a paginated list of agents, newest first.",
)
async def list_all(
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Optional status filter (ACTIVE or FROZEN).",
        examples=["ACTIVE"],
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AgentListResponse:
    """List agents."""
    from app.core.constants import AgentStatus

    status_enum = None
    if status_filter is not None:
        try:
            status_enum = AgentStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status_filter}'. Use ACTIVE or FROZEN.",
            )

    agents, total = await agent_service.list_agents(
        session, status=status_enum, skip=skip, limit=limit, user_id=user.id,
    )
    for a in agents:
        await populate_agent_limits(session, a)
    return AgentListResponse(
        total=total,
        agents=[AgentResponse.model_validate(a) for a in agents],
    )


# =============================================================================
# GET /agents/{id}
# =============================================================================

@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get a single agent by ID",
    responses={404: {"description": "Agent not found."}},
)
async def get_one(
    agent_id: str,
    session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AgentResponse:
    """Get agent by ID or name."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    await populate_agent_limits(session, agent)
    return AgentResponse.model_validate(agent)



# =============================================================================
# PUT /agents/{id}
# =============================================================================

@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Partially update an agent",
    description="Only the fields you send are changed.  **Requires ``admin`` or ``owner``.**",
    responses={404: {"description": "Agent not found."}},
)
async def update_one(
    agent_id: str,
    body: AgentUpdate,
    session = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> AgentResponse:
    """Partially update an agent."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    # Name-uniqueness check (if name is being changed)
    if body.name is not None and body.name != agent.name:
        existing = await agent_service.get_agent_by_name(session, body.name, user_id=user.id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent '{body.name}' already exists.",
            )

    updated = await agent_service.update_agent(
        session, agent,
        name=body.name,
        description=body.description,
        balance=body.balance,
        per_transaction_limit=body.per_transaction_limit,
        daily_limit=body.daily_limit,
        max_requests_per_minute=body.max_requests_per_minute,
    )
    await populate_agent_limits(session, updated)
    return AgentResponse.model_validate(updated)


# =============================================================================
# DELETE /agents/{id}
# =============================================================================

@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an agent",
    description="Permanently deletes the agent and its allowlist entries.  **Requires ``admin`` or ``owner``.**",
    responses={
        204: {"description": "Agent deleted."},
        404: {"description": "Agent not found."},
    },
)
async def delete_one(
    agent_id: str,
    session = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> None:
    """Delete an agent."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    await agent_service.delete_agent(session, agent)


# =============================================================================
# POST /agents/{id}/freeze
# =============================================================================

@router.post(
    "/{agent_id}/freeze",
    response_model=AgentResponse,
    summary="Freeze an agent (kill switch)",
    description="Changes agent status to FROZEN — **all future payment requests are blocked**.  **Requires ``admin`` or ``owner``.**",
    responses={404: {"description": "Agent not found."}},
)
async def freeze(
    agent_id: str,
    session = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> AgentResponse:
    """Freeze an agent."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    agent = await agent_service.freeze_agent(session, agent)
    await populate_agent_limits(session, agent)
    return AgentResponse.model_validate(agent)


# =============================================================================
# POST /agents/{id}/unfreeze
# =============================================================================

@router.post(
    "/{agent_id}/unfreeze",
    response_model=AgentResponse,
    summary="Unfreeze an agent",
    description="Changes agent status back to ACTIVE.  **Requires ``admin`` or ``owner``.**",
    responses={404: {"description": "Agent not found."}},
)
async def unfreeze(
    agent_id: str,
    session = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> AgentResponse:
    """Unfreeze an agent."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    agent = await agent_service.unfreeze_agent(session, agent)
    await populate_agent_limits(session, agent)
    return AgentResponse.model_validate(agent)


# =============================================================================
# PUT /agents/{id}/policy
# =============================================================================

@router.put(
    "/{agent_id}/policy",
    response_model=AgentResponse,
    summary="Update agent spending policy",
    description="""
Change an agent's spending limits.  Only the fields you send are updated;
omitted fields keep their current values.

**Changes take effect immediately** — the next payment request will be
evaluated against the new limits.

### Example

    PUT /agents/1/policy
    {
        "per_transaction_limit": 2000.0,
        "daily_limit": 10000.0
    }

**Requires ``admin`` or ``owner``.**
""",
    responses={
        200: {"description": "Policy updated."},
        404: {"description": "Agent not found."},
        422: {"description": "Validation error."},
    },
)
async def update_policy(
    agent_id: str,
    body: PolicyUpdate,
    session = Depends(get_session),
    user: User = Depends(RequireAdmin),
) -> AgentResponse:
    """Update an agent's spending policy."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    updated = await agent_service.update_agent(
        session,
        agent,
        per_transaction_limit=body.per_transaction_limit,
        daily_limit=body.daily_limit,
        max_requests_per_minute=body.max_requests_per_minute,
    )
    await populate_agent_limits(session, updated)
    return AgentResponse.model_validate(updated)


# =============================================================================
# GET /agents/{id}/transactions
# =============================================================================

from datetime import datetime
from pydantic import BaseModel

class AgentTransactionItem(BaseModel):
    id: int
    request_id: str
    agent_id: int | None
    merchant_id: int | None
    amount: float
    status: str
    reason: str | None
    created_at: datetime
    settled_at: datetime | None = None

    model_config = {"from_attributes": True}


@router.get(
    "/{agent_id}/transactions",
    response_model=list[AgentTransactionItem],
    summary="Get an agent's transaction history",
    responses={404: {"description": "Agent not found."}},
)
async def get_agent_transactions(
    agent_id: str,
    session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[AgentTransactionItem]:
    """Get transactions/payment requests for an agent."""
    agent = await agent_service.get_agent_by_identifier(session, agent_id, user_id=user.id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    from datetime import datetime, timezone
    reqs_data = await session.query("payment_requests", [("agent_id", "==", agent.id)])
    
    # Sort locally by created_at desc
    def get_created_at(pr_dict):
        ca = pr_dict.get("created_at")
        if ca is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if hasattr(ca, "to_datetime"):
            return ca.to_datetime()
        if isinstance(ca, str):
            try:
                return datetime.fromisoformat(ca.replace("Z", "+00:00"))
            except ValueError:
                pass
        return ca
        
    reqs_data.sort(key=get_created_at, reverse=True)

    items = []
    for r in reqs_data:
        created_at_dt = get_created_at(r)
        settled_at = created_at_dt if r.get("status") == "SETTLED" else None
        items.append(
            AgentTransactionItem(
                id=r.get("id"),
                request_id=r.get("request_id"),
                agent_id=r.get("agent_id"),
                merchant_id=r.get("merchant_id"),
                amount=r.get("amount"),
                status=r.get("status"),
                reason=r.get("reason"),
                created_at=created_at_dt,
                settled_at=settled_at,
            )
        )
    return items

