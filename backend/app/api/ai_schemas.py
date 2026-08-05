"""AI-related Pydantic schemas — request/response models for AI endpoints."""

from pydantic import BaseModel, Field




class ExplainBlockedRequest(BaseModel):
    """Body for ``POST /ai/explain-blocked``.

    Example:
        {
            "request_id": "req_1042",
            "agent_name": "ShoppingAgent-01",
            "merchant_name": "Compute Provider",
            "amount": 2000.0,
            "reason": "PER_TX_LIMIT_EXCEEDED"
        }
    """
    request_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        examples=["req_1042"],
        description="The blocked payment request ID.",
    )
    agent_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        examples=["ShoppingAgent-01"],
    )
    merchant_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Compute Provider"],
    )
    amount: float = Field(
        ...,
        gt=0.0,
        examples=[2_000.0],
    )
    reason: str = Field(
        ...,
        examples=["PER_TX_LIMIT_EXCEEDED"],
        description="The rejection reason from the policy engine.",
    )




class ExplainPolicyRequest(BaseModel):
    """Body for ``POST /ai/explain-policy``.

    Example:
        {
            "agent_name": "ShoppingAgent-01",
            "per_transaction_limit": 1000.0,
            "daily_limit": 5000.0,
            "max_requests_per_minute": 5,
            "balance": 10000.0,
            "status": "ACTIVE"
        }
    """
    agent_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        examples=["ShoppingAgent-01"],
    )
    per_transaction_limit: float | None = Field(
        default=None, gt=0.0, examples=[1_000.0],
    )
    daily_limit: float | None = Field(
        default=None, gt=0.0, examples=[5_000.0],
    )
    max_requests_per_minute: int | None = Field(
        default=None, ge=1, examples=[5],
    )
    balance: float | None = Field(
        default=None, examples=[10_000.0],
    )
    status: str | None = Field(
        default=None, examples=["ACTIVE"],
    )




class AIExplanation(BaseModel):
    """A single AI-generated (or fallback) explanation.

    Example:
        {
            "explanation": "Agent ShoppingAgent-01 is frozen by the owner...",
            "provider": "fallback"
        }
    """
    explanation: str = Field(
        ...,
        examples=["Agent 'ShoppingAgent-01' is currently frozen…"],
        description="Human-readable explanation in plain English.",
    )
    provider: str = Field(
        ...,
        examples=["groq", "gemini", "fallback"],
        description="Which AI provider generated this (or 'fallback').",
    )
