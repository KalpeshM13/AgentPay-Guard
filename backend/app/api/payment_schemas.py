"""Payment-related Pydantic schemas — request bodies and response models.

Added to the shared ``app.api.schemas`` namespace.
"""

from datetime import datetime

from pydantic import BaseModel, Field



class PaymentRequestSchema(BaseModel):
    """Body for ``POST /payments`` — what the agent sends.

    Example:
        {
            "request_id": "req_1042",
            "agent_id": 1,
            "merchant_id": 2,
            "amount": 300.0
        }
    """
    request_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        examples=["req_1042"],
        description="Unique idempotency key for this payment attempt.",
    )
    agent_id: int = Field(
        ...,
        gt=0,
        examples=[1],
        description="ID of the agent making the payment request.",
    )
    merchant_id: int = Field(
        ...,
        gt=0,
        examples=[2],
        description="ID of the merchant to pay.",
    )
    amount: float = Field(
        ...,
        gt=0.0,
        examples=[300.0],
        description="Amount to pay (must be > 0).",
    )



class PaymentResponse(BaseModel):
    """Returned after the full policy + executor pipeline.

    Example (approved):
        {
            "request_id": "req_1042",
            "status": "SETTLED",
            "amount": 300.0,
            "balance_after": 9700.0,
            "remaining_daily_limit": 4700.0
        }

    Example (blocked):
        {
            "request_id": "req_1042",
            "status": "BLOCKED",
            "reason": "AGENT_FROZEN",
            "amount": 300.0
        }
    """
    request_id: str
    status: str = Field(..., examples=["SETTLED"])
    reason: str | None = Field(
        default=None, examples=[None],
        description="Rejection reason when status is BLOCKED.",
    )
    amount: float
    balance_after: float | None = Field(
        default=None,
        examples=[9_700.0],
        description="Agent balance after settlement (null when blocked).",
    )
    remaining_daily_limit: float | None = Field(
        default=None,
        examples=[4_700.0],
        description="Remaining daily spend allowance after this payment.",
    )



class PaymentRequestItem(BaseModel):
    """Single item in the transaction / audit log feed."""
    id: int
    request_id: str
    agent_id: int | None
    merchant_id: int | None
    amount: float
    status: str
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentRequestListResponse(BaseModel):
    """Paginated list of payment requests for the dashboard."""
    total: int
    items: list[PaymentRequestItem]
