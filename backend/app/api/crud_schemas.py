"""Pydantic schemas for Agent, Merchant, and Allowlist CRUD endpoints.

Every schema includes ``examples=`` so Swagger shows realistic sample payloads.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import AgentStatus


# =============================================================================
# Agent schemas
# =============================================================================

class AgentCreate(BaseModel):
    """Body for ``POST /agents`` — create a new autonomous agent.

    Example:
        {
            "name": "ShoppingAgent-01",
            "description": "Handles compute-credit purchases for the research team.",
            "balance": 10000.0,
            "per_transaction_limit": 1000.0,
            "daily_limit": 5000.0,
            "max_requests_per_minute": 5
        }
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        examples=["ShoppingAgent-01"],
        description="Unique human-readable label. Shown on the dashboard.",
    )
    description: str | None = Field(
        default=None,
        examples=["Handles compute-credit purchases for the research team."],
        description="Optional free-text describing the agent's purpose.",
    )
    balance: float = Field(
        default=0.0,
        ge=0.0,
        examples=[10_000.0],
        description="Starting simulated wallet balance (non-negative).",
    )
    per_transaction_limit: float = Field(
        ...,
        gt=0.0,
        examples=[1_000.0],
        description="Maximum amount per single payment request.",
    )
    daily_limit: float = Field(
        ...,
        gt=0.0,
        examples=[5_000.0],
        description="Maximum cumulative spend per calendar day.",
    )
    max_requests_per_minute: int = Field(
        default=10,
        ge=1,
        examples=[5],
        description="Rate-limit: max payment requests per sliding minute.",
    )


class AgentUpdate(BaseModel):
    """Body for ``PUT /agents/{id}`` — partial update of an agent.

    Only the fields you include are changed; omitted fields stay as-is.
    """
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
        examples=["ShoppingAgent-01-v2"],
        description="New display name (unique).",
    )
    description: str | None = Field(
        default=None,
        examples=["Updated description."],
        description="New description.",
    )
    balance: float | None = Field(
        default=None,
        ge=0.0,
        examples=[20_000.0],
        description="New simulated balance.",
    )
    per_transaction_limit: float | None = Field(
        default=None,
        gt=0.0,
        examples=[2_000.0],
        description="New per-transaction limit.",
    )
    daily_limit: float | None = Field(
        default=None,
        gt=0.0,
        examples=[10_000.0],
        description="New daily cumulative limit.",
    )
    max_requests_per_minute: int | None = Field(
        default=None,
        ge=1,
        examples=[10],
        description="New rate-limit.",
    )


class AgentResponse(BaseModel):
    """Returned by all Agent endpoints.

    Example:
        {
            "id": 1,
            "name": "ShoppingAgent-01",
            "description": "Handles compute-credit purchases.",
            "status": "ACTIVE",
            "balance": 10000.0,
            "per_transaction_limit": 1000.0,
            "daily_limit": 5000.0,
            "max_requests_per_minute": 5,
            "allowlist": [],
            "created_at": "2026-08-01T14:30:00Z",
            "updated_at": "2026-08-01T14:30:00Z"
        }
    """
    id: int
    name: str
    description: str | None
    status: AgentStatus
    balance: float
    per_transaction_limit: float
    per_tx_limit: float = 0.0
    daily_limit: float
    max_requests_per_minute: int
    allowlist: list["MerchantResponse"] = Field(default=[])
    spent_today: float = 0.0
    remaining_daily_limit: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Wrapper for ``GET /agents`` — returns a list plus the total count."""
    total: int = Field(..., examples=[3])
    agents: list[AgentResponse]


# =============================================================================
# Policy update schema (dedicated route for clarity)
# =============================================================================

class PolicyUpdate(BaseModel):
    """Body for ``PUT /agents/{id}/policy`` — update spending rules.

    Only the fields you include are changed; omitted fields stay as-is.
    Changes take effect **immediately** on the next payment request.

    Example:
        {
            "per_transaction_limit": 2000.0,
            "daily_limit": 10000.0,
            "max_requests_per_minute": 10
        }
    """
    per_transaction_limit: float | None = Field(
        default=None,
        gt=0.0,
        examples=[2_000.0],
        description="New per-transaction maximum (must be > 0).",
    )
    daily_limit: float | None = Field(
        default=None,
        gt=0.0,
        examples=[10_000.0],
        description="New daily cumulative maximum (must be > 0).",
    )
    max_requests_per_minute: int | None = Field(
        default=None,
        ge=1,
        examples=[10],
        description="New rate-limit (must be ≥ 1).",
    )


# =============================================================================
# Merchant schemas
# =============================================================================

class MerchantCreate(BaseModel):
    """Body for ``POST /merchants``.

    Example:
        {
            "display_name": "Compute Provider",
            "destination_reference": "merchant_compute_01",
            "description": "Primary cloud compute vendor."
        }
    """
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Compute Provider"],
        description="Human-readable merchant label.",
    )
    destination_reference: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["merchant_compute_01"],
        description="Identifier the Payment Executor uses to route funds.",
    )
    description: str | None = Field(
        default=None,
        examples=["Primary cloud compute vendor."],
        description="Optional note.",
    )


class MerchantResponse(BaseModel):
    """Returned by Merchant endpoints.

    Example:
        {
            "id": 1,
            "display_name": "Compute Provider",
            "destination_reference": "merchant_compute_01",
            "description": "Primary cloud compute vendor.",
            "active": true,
            "created_at": "2026-08-01T14:30:00Z"
        }
    """
    id: int
    display_name: str
    destination_reference: str
    description: str | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MerchantListResponse(BaseModel):
    """Wrapper for ``GET /merchants``."""
    total: int
    merchants: list[MerchantResponse]


# =============================================================================
# Allowlist schemas
# =============================================================================

class AllowlistAdd(BaseModel):
    """Body for ``POST /agents/{id}/allowlist``."""
    merchant_id: int | str = Field(
        ...,
        examples=[1, "merchant_aws_01"],
        description="ID or reference of merchant to add to allowlist.",
    )
    display_name: str | None = Field(default=None, examples=["Amazon Web Services"])
    destination_reference: str | None = Field(default=None, examples=["0x91CA..."])


class AllowlistEntryResponse(BaseModel):
    """A single allowlist entry returned by ``GET /agents/{id}/allowlist``.

    Example:
        {
            "id": 1,
            "agent_id": 2,
            "merchant_id": 3,
            "merchant_name": "Compute Provider",
            "created_at": "2026-08-01T14:30:00Z"
        }
    """
    id: int
    agent_id: int
    merchant_id: int
    merchant_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AllowlistResponse(BaseModel):
    """Wrapper for ``GET /agents/{id}/allowlist``."""
    agent_id: int
    total: int
    allowlist: list[AllowlistEntryResponse]


# Rebuild model to resolve forward references
AgentResponse.model_rebuild()
