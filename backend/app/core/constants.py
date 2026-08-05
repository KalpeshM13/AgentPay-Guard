"""Project-wide constants.

These differ from Settings in that they are NOT expected to change
between deployments – they define the shape of the domain.
"""

from enum import StrEnum


class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"


class AgentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    SETTLED = "SETTLED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class RejectionReason:
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_FROZEN = "AGENT_FROZEN"
    MERCHANT_NOT_FOUND = "MERCHANT_NOT_FOUND"
    MERCHANT_NOT_ACTIVE = "MERCHANT_NOT_ACTIVE"
    MERCHANT_NOT_ALLOWED = "MERCHANT_NOT_ALLOWED"
    PER_TX_LIMIT_EXCEEDED = "PER_TX_LIMIT_EXCEEDED"
    DAILY_LIMIT_EXCEEDED = "DAILY_LIMIT_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"


class AuditEventType(StrEnum):
    AGENT_CREATED = "agent_created"
    AGENT_FROZEN = "agent_frozen"
    AGENT_UNFROZEN = "agent_unfrozen"
    POLICY_UPDATED = "policy_updated"
    MERCHANT_ADDED = "merchant_added"
    MERCHANT_REMOVED = "merchant_removed"
    PAYMENT_REQUESTED = "payment_requested"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_BLOCKED = "payment_blocked"
    PAYMENT_SETTLED = "payment_settled"
    PAYMENT_CANCELLED = "payment_cancelled"
