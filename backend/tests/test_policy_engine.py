"""Independent unit tests for the Policy Engine.

These tests run **without a database connection** — every dependency is
injected via callbacks so the engine can be tested in complete isolation.

Run with::

    pytest tests/test_policy_engine.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.constants import AgentStatus, RejectionReason
from app.services.policy_engine import PolicyContext, PolicyDecision, evaluate


# =============================================================================
# Helpers — lightweight fakes that mimic ORM models enough for the engine
# =============================================================================


class FakeAgent:
    """Minimal agent stub for policy tests."""

    def __init__(
        self,
        agent_id: int = 1,
        status: AgentStatus = AgentStatus.ACTIVE,
        per_transaction_limit: float = 1_000.0,
        daily_limit: float = 5_000.0,
        max_requests_per_minute: int = 10,
        balance: float = 10_000.0,
    ):
        self.id = agent_id
        self.status = status
        self.per_transaction_limit = per_transaction_limit
        self.daily_limit = daily_limit
        self.max_requests_per_minute = max_requests_per_minute
        self.balance = balance


class FakeMerchant:
    """Minimal merchant stub for policy tests."""

    def __init__(
        self, merchant_id: int = 1, active: bool = True,
    ):
        self.id = merchant_id
        self.active = active


# =============================================================================
# Default callbacks — return "clean" values (all checks pass)
# =============================================================================

async def _daily_spend_zero(_agent_id: int) -> float:
    return 0.0


async def _rate_under_limit(_agent_id: int, _ts: datetime) -> int:
    return 0


async def _not_duplicate(_request_id: str) -> bool:
    return False


# =============================================================================
# Context builder
# =============================================================================

_UNSET = object()


def make_context(
    *,
    agent: FakeAgent | None = _UNSET,           # type: ignore[assignment]
    merchant: FakeMerchant | None = _UNSET,      # type: ignore[assignment]
    is_allowlisted: bool = True,
    amount: float = 500.0,
    request_id: str = "req_test_001",
    get_daily_spend=None,
    count_recent=None,
    is_duplicate=None,
) -> PolicyContext:
    """Build a PolicyContext with sensible defaults for a passing request.

    Pass ``agent=None`` or ``merchant=None`` explicitly to test missing-entity
    scenarios.  Omit them (or leave as default) to get healthy defaults.
    """
    return PolicyContext(
        request_id=request_id,
        request_timestamp=datetime.now(timezone.utc),
        agent=FakeAgent() if agent is _UNSET else agent,
        merchant=FakeMerchant() if merchant is _UNSET else merchant,
        is_merchant_allowlisted=is_allowlisted,
        amount=amount,
        get_daily_spend=get_daily_spend or _daily_spend_zero,
        count_recent_requests=count_recent or _rate_under_limit,
        is_duplicate_request_id=is_duplicate or _not_duplicate,
    )


# =============================================================================
# Tests — all-OK
# =============================================================================


@pytest.mark.asyncio
async def test_all_checks_pass_returns_approved():
    """A valid request with all checks green should be APPROVED."""
    ctx = make_context()
    decision = await evaluate(ctx)

    assert decision.approved is True
    assert decision.reason is None
    assert decision.details["request_id"] == "req_test_001"
    assert decision.details["agent_id"] == 1
    assert decision.details["merchant_id"] == 1
    assert decision.details["amount"] == 500.0


# =============================================================================
# Check 1 — Agent exists
# =============================================================================


@pytest.mark.asyncio
async def test_check_1_agent_not_found():
    ctx = make_context(agent=None)
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.AGENT_NOT_FOUND
    assert decision.details["failed_at"] == "check_1_agent_exists"
    assert decision.details["agent_id"] is None


# =============================================================================
# Check 2 — Agent ACTIVE
# =============================================================================


@pytest.mark.asyncio
async def test_check_2_agent_frozen():
    ctx = make_context(agent=FakeAgent(status=AgentStatus.FROZEN))
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.AGENT_FROZEN
    assert decision.details["failed_at"] == "check_2_agent_active"
    assert decision.details["agent_status"] == "FROZEN"


# =============================================================================
# Check 3 — Merchant exists
# =============================================================================


@pytest.mark.asyncio
async def test_check_3_merchant_not_found():
    ctx = make_context(merchant=None)
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.MERCHANT_NOT_FOUND
    assert decision.details["failed_at"] == "check_3_merchant_exists"


# =============================================================================
# Check 4 — Merchant ACTIVE
# =============================================================================


@pytest.mark.asyncio
async def test_check_4_merchant_not_active():
    ctx = make_context(merchant=FakeMerchant(active=False))
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.MERCHANT_NOT_ACTIVE
    assert decision.details["failed_at"] == "check_4_merchant_active"


# =============================================================================
# Check 5 — Merchant allowlisted
# =============================================================================


@pytest.mark.asyncio
async def test_check_5_merchant_not_allowlisted():
    ctx = make_context(is_allowlisted=False)
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.MERCHANT_NOT_ALLOWED
    assert decision.details["failed_at"] == "check_5_merchant_allowlisted"


# =============================================================================
# Check 6 — Per-transaction limit
# =============================================================================


@pytest.mark.asyncio
async def test_check_6_exactly_at_limit_approved():
    """amount == limit should pass (not >)."""
    ctx = make_context(agent=FakeAgent(per_transaction_limit=1_000.0), amount=1_000.0)
    decision = await evaluate(ctx)
    assert decision.approved is True


@pytest.mark.asyncio
async def test_check_6_over_limit_blocked():
    ctx = make_context(agent=FakeAgent(per_transaction_limit=1_000.0), amount=1_001.0)
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.PER_TX_LIMIT_EXCEEDED
    assert decision.details["failed_at"] == "check_6_per_tx_limit"
    assert decision.details["per_transaction_limit"] == 1_000.0


# =============================================================================
# Check 7 — Daily spend limit
# =============================================================================


@pytest.mark.asyncio
async def test_check_7_within_daily_limit_approved():
    ctx = make_context(
        agent=FakeAgent(daily_limit=5_000.0),
        amount=500.0,
        get_daily_spend=async_fn(return_value=4_000.0),
    )
    decision = await evaluate(ctx)
    assert decision.approved is True  # 4000 + 500 = 4500 ≤ 5000


@pytest.mark.asyncio
async def test_check_7_exceeds_daily_limit_blocked():
    ctx = make_context(
        agent=FakeAgent(daily_limit=5_000.0),
        amount=500.0,
        get_daily_spend=async_fn(return_value=4_600.0),
    )
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.DAILY_LIMIT_EXCEEDED
    assert decision.details["failed_at"] == "check_7_daily_limit"
    assert decision.details["spent_today"] == 4_600.0
    assert decision.details["daily_limit"] == 5_000.0


@pytest.mark.asyncio
async def test_check_7_exactly_at_daily_limit_approved():
    ctx = make_context(
        agent=FakeAgent(daily_limit=5_000.0),
        amount=1_000.0,
        get_daily_spend=async_fn(return_value=4_000.0),
    )
    decision = await evaluate(ctx)
    assert decision.approved is True  # 4000 + 1000 = 5000 OK


# =============================================================================
# Check 8 — Rate limit (requests / minute)
# =============================================================================


@pytest.mark.asyncio
async def test_check_8_rate_under_limit_approved():
    ctx = make_context(
        agent=FakeAgent(max_requests_per_minute=5),
        count_recent=async_fn(return_value=3),
    )
    decision = await evaluate(ctx)
    assert decision.approved is True  # 3 < 5


@pytest.mark.asyncio
async def test_check_8_rate_at_limit_blocked():
    ctx = make_context(
        agent=FakeAgent(max_requests_per_minute=5),
        count_recent=async_fn(return_value=5),
    )
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.RATE_LIMIT_EXCEEDED
    assert decision.details["failed_at"] == "check_8_rate_limit"
    assert decision.details["current_rate"] == 5
    assert decision.details["max_rate"] == 5


@pytest.mark.asyncio
async def test_check_8_rate_over_limit_blocked():
    ctx = make_context(
        agent=FakeAgent(max_requests_per_minute=5),
        count_recent=async_fn(return_value=6),
    )
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.RATE_LIMIT_EXCEEDED


# =============================================================================
# Check 9 — Duplicate request_id
# =============================================================================


@pytest.mark.asyncio
async def test_check_9_unique_request_id_approved():
    ctx = make_context(is_duplicate=async_fn(return_value=False))
    decision = await evaluate(ctx)
    assert decision.approved is True


@pytest.mark.asyncio
async def test_check_9_duplicate_request_id_blocked():
    ctx = make_context(is_duplicate=async_fn(return_value=True))
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.DUPLICATE_REQUEST
    assert decision.details["failed_at"] == "check_9_duplicate_request_id"


# =============================================================================
# Check 10 — Wallet balance
# =============================================================================


@pytest.mark.asyncio
async def test_check_10_sufficient_balance_approved():
    ctx = make_context(agent=FakeAgent(balance=500.0), amount=500.0)
    decision = await evaluate(ctx)
    assert decision.approved is True  # exact match OK


@pytest.mark.asyncio
async def test_check_10_insufficient_balance_blocked():
    ctx = make_context(agent=FakeAgent(balance=100.0), amount=101.0)
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.INSUFFICIENT_BALANCE
    assert decision.details["failed_at"] == "check_10_balance"
    assert decision.details["balance"] == 100.0


# =============================================================================
# Edge cases
# =============================================================================


@pytest.mark.asyncio
async def test_zero_amount_passes_all_checks():
    """A zero-amount payment should pass all numeric checks."""
    ctx = make_context(amount=0.0)
    decision = await evaluate(ctx)
    assert decision.approved is True


@pytest.mark.asyncio
async def test_negative_amount_passes_all_checks():
    """Negative amounts are not rejected by the engine (validation happens earlier)."""
    ctx = make_context(agent=FakeAgent(per_transaction_limit=1000), amount=-50.0)
    decision = await evaluate(ctx)
    assert decision.approved is True


@pytest.mark.asyncio
async def test_first_check_fails_short_circuits():
    """When agent is None, only check 1 should run (not checks 3–10)."""
    # Merchant is also None, but we should get AGENT_NOT_FOUND, not MERCHANT_NOT_FOUND
    ctx = make_context(agent=None, merchant=None)
    decision = await evaluate(ctx)

    assert decision.approved is False
    assert decision.reason == RejectionReason.AGENT_NOT_FOUND
    # Check that we hit check 1, not check 3
    assert decision.details["failed_at"] == "check_1_agent_exists"


@pytest.mark.asyncio
async def test_agent_frozen_before_merchant_checks():
    """When agent is frozen AND merchant is missing, AGENT_FROZEN wins."""
    ctx = make_context(agent=FakeAgent(status=AgentStatus.FROZEN), merchant=None)
    decision = await evaluate(ctx)

    assert decision.reason == RejectionReason.AGENT_FROZEN
    assert decision.details["failed_at"] == "check_2_agent_active"


@pytest.mark.asyncio
async def test_decision_repr():
    d = PolicyDecision.approve(request_id="r1")
    assert "APPROVED" in repr(d)

    d2 = PolicyDecision.block(RejectionReason.AGENT_FROZEN, failed_at="x", request_id="r2")
    assert "BLOCKED" in repr(d2)
    assert "AGENT_FROZEN" in repr(d2)


@pytest.mark.asyncio
async def test_all_rejection_reasons_are_unique():
    """Ensure every rejection reason is distinct."""
    reasons = {
        RejectionReason.AGENT_NOT_FOUND,
        RejectionReason.AGENT_FROZEN,
        RejectionReason.MERCHANT_NOT_FOUND,
        RejectionReason.MERCHANT_NOT_ACTIVE,
        RejectionReason.MERCHANT_NOT_ALLOWED,
        RejectionReason.PER_TX_LIMIT_EXCEEDED,
        RejectionReason.DAILY_LIMIT_EXCEEDED,
        RejectionReason.RATE_LIMIT_EXCEEDED,
        RejectionReason.DUPLICATE_REQUEST,
        RejectionReason.INSUFFICIENT_BALANCE,
    }
    assert len(reasons) == 10


# =============================================================================
# Helper — dynamically create async functions with controlled return values
# =============================================================================

def async_fn(*, return_value):
    """Return an async callable that always returns *return_value*.

    Usage::

        ctx = make_context(get_daily_spend=async_fn(return_value=4_600.0))
    """
    async def _fn(*args, **kwargs):
        return return_value
    return _fn
