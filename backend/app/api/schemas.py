"""Pydantic request/response schemas shared across API endpoints."""


# ---------------------------------------------------------------------------
# Re-export everything from all schema modules
# ---------------------------------------------------------------------------
from app.api.ai_schemas import (  # noqa: F401
    AIExplanation,
    ExplainBlockedRequest,
    ExplainPolicyRequest,
)
from app.api.auth_schemas import (  # noqa: F401
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.api.crud_schemas import (  # noqa: F401
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    AllowlistAdd,
    AllowlistEntryResponse,
    AllowlistResponse,
    MerchantCreate,
    MerchantListResponse,
    MerchantResponse,
    PolicyUpdate,
)
from app.api.dashboard_schemas import (  # noqa: F401
    ActivityFilter,
    ActivityItem,
    ActivityResponse,
    AuditFilter,
    AuditItem,
    AuditResponse,
    DashboardSummary,
)
from app.api.payment_schemas import (  # noqa: F401
    PaymentRequestItem,
    PaymentRequestListResponse,
    PaymentRequestSchema,
    PaymentResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    # Agents
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentListResponse",
    "PolicyUpdate",
    # Merchants
    "MerchantCreate",
    "MerchantResponse",
    "MerchantListResponse",
    # Allowlist
    "AllowlistAdd",
    "AllowlistEntryResponse",
    "AllowlistResponse",
    # Payments
    "PaymentRequestSchema",
    "PaymentResponse",
    "PaymentRequestItem",
    "PaymentRequestListResponse",
    # Dashboard
    "DashboardSummary",
    "ActivityFilter",
    "ActivityItem",
    "ActivityResponse",
    "AuditFilter",
    "AuditItem",
    "AuditResponse",
    # AI
    "AIExplanation",
    "ExplainBlockedRequest",
    "ExplainPolicyRequest",
]
