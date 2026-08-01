"""Policy Engine — the independent payment-decision authority.

This module implements the *complete* decision logic from Section 8 of the
blueprint.  It is intentionally **free of side effects** — it never writes
to the database, never modifies balances, and never executes payments.

Design
------
The engine is a single async function ``evaluate()`` that receives a
``PolicyContext`` (the data it needs) and returns a ``PolicyDecision``.

All 10 checks run **in order**.  The first check that fails produces a
``BLOCKED`` decision with a **canonical rejection reason**.  If all checks
pass, the decision is ``APPROVED``.

Checks (in order)
-----------------
1.  Agent exists
2.  Agent is ACTIVE
3.  Merchant exists
4.  Merchant is ACTIVE
5.  Merchant is on the agent's allowlist
6.  Amount ≤ per-transaction limit
7.  (today's approved spend + amount) ≤ daily limit
8.  Rate (requests/minute) ≤ max requests/minute
9.  request_id is not a duplicate
10. Amount ≤ current wallet balance

Independently testable
----------------------
The engine accepts *injected* callables for daily-spend and duplicate-detection
so that tests can control every input without populating a real database.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.constants import AgentStatus, RejectionReason

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.merchant import Merchant

logger = logging.getLogger(__name__)

# =============================================================================
# Public types
# =============================================================================


@dataclass
class PolicyDecision:
    """The result of a policy evaluation.

    Attributes
    ----------
    approved : bool
        ``True`` if all checks passed, ``False`` otherwise.
    reason : str | None
        When not approved, the ``RejectionReason`` constant explaining why.
        ``None`` when approved.
    details : dict
        Additional context for logging / audit.  Always includes the
        ``request_id``, ``agent_id``, ``merchant_id``, ``amount``, and
        the check that failed (key ``failed_at``).
    """

    approved: bool
    reason: str | None = None
    details: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------
    @classmethod
    def approve(cls, **details) -> PolicyDecision:
        """Return an approved decision with extra context."""
        return cls(approved=True, reason=None, details=details)

    @classmethod
    def block(cls, reason: str, failed_at: str, **details) -> PolicyDecision:
        """Return a blocked decision with the rejection reason and extra context."""
        details["failed_at"] = failed_at
        return cls(approved=False, reason=reason, details=details)

    def __repr__(self) -> str:
        status = "APPROVED" if self.approved else f"BLOCKED: {self.reason}"
        rid = self.details.get("request_id", "?")
        return f"<PolicyDecision {status} request={rid}>"


# =============================================================================
# Policy input — the data the engine needs to make a decision
# =============================================================================


@dataclass
class PolicyContext:
    """All the data the policy engine requires to evaluate one payment request.

    The engine does **not** fetch data — it only reads what is passed in
    this context.  The caller is responsible for loading models and providing
    the two async callbacks for data the engine cannot derive from the models
    alone.

    Attributes
    ----------
    request_id : str
        Unique idempotency key for this payment request.
    request_timestamp : datetime
        When the request arrived (for rate-limit calculation).
    agent : Agent | None
        The resolved agent model, or ``None`` if not found.
    merchant : Merchant | None
        The resolved merchant model, or ``None`` if not found.
    is_merchant_allowlisted : bool
        Whether *agent* has *merchant* on its allowlist (pre-checked).
    amount : float
        The requested payment amount.
    get_daily_spend : Callable
        Called as ``get_daily_spend(agent_id) → float`` to get the total
        approved/settled spend for *today*.  Must be injected by the caller.
    count_recent_requests : Callable
        Called as ``count_recent_requests(agent_id, window_start) → int``
        to count how many payment requests this agent has made in the
        rate-limit window.  Must be injected by the caller.
    is_duplicate_request_id : Callable
        Called as ``is_duplicate_request_id(request_id) → bool``
        to check whether the request_id has been seen before.  Must be
        injected by the caller.
    """

    request_id: str
    request_timestamp: datetime
    agent: Agent | None
    merchant: Merchant | None
    is_merchant_allowlisted: bool
    amount: float

    # Injected async callbacks — these decouple the engine from the database
    get_daily_spend: Callable[[int], Awaitable[float]]
    count_recent_requests: Callable[[int, datetime], Awaitable[int]]
    is_duplicate_request_id: Callable[[str], Awaitable[bool]]


# =============================================================================
# The engine
# =============================================================================


async def evaluate(ctx: PolicyContext) -> PolicyDecision:
    """Run all 10 policy checks in order and return a decision.

    This is the **only** public entry point.  It is stateless and raises no
    exceptions — every outcome is captured as a ``PolicyDecision``.

    Parameters
    ----------
    ctx : PolicyContext
        All inputs the engine needs.

    Returns
    -------
    PolicyDecision
        ``.approved`` is ``True`` only when every check passes.
    """
    base = {
        "request_id": ctx.request_id,
        "agent_id": ctx.agent.id if ctx.agent else None,
        "merchant_id": ctx.merchant.id if ctx.merchant else None,
        "amount": ctx.amount,
    }

    # ── Check 1: Agent exists ──────────────────────────────────────────
    if ctx.agent is None:
        logger.info("Policy check 1 failed: AGENT_NOT_FOUND")
        return PolicyDecision.block(
            RejectionReason.AGENT_NOT_FOUND,
            failed_at="check_1_agent_exists",
            **base,
        )

    agent: Agent = ctx.agent  # narrow type for the rest of the function

    # ── Check 2: Agent ACTIVE ──────────────────────────────────────────
    if agent.status != AgentStatus.ACTIVE:
        logger.info(
            "Policy check 2 failed: AGENT_FROZEN agent_id=%d status=%s",
            agent.id, agent.status.value,
        )
        return PolicyDecision.block(
            RejectionReason.AGENT_FROZEN,
            failed_at="check_2_agent_active",
            agent_status=agent.status.value,
            **base,
        )

    # ── Check 3: Merchant exists ───────────────────────────────────────
    if ctx.merchant is None:
        logger.info("Policy check 3 failed: MERCHANT_NOT_FOUND")
        return PolicyDecision.block(
            RejectionReason.MERCHANT_NOT_FOUND,
            failed_at="check_3_merchant_exists",
            **base,
        )

    merchant: Merchant = ctx.merchant  # narrow type

    # ── Check 4: Merchant ACTIVE ───────────────────────────────────────
    if not merchant.active:
        logger.info(
            "Policy check 4 failed: MERCHANT_NOT_ACTIVE merchant_id=%d",
            merchant.id,
        )
        return PolicyDecision.block(
            RejectionReason.MERCHANT_NOT_ACTIVE,
            failed_at="check_4_merchant_active",
            **base,
        )

    # ── Check 5: Merchant allowlisted ──────────────────────────────────
    if not ctx.is_merchant_allowlisted:
        logger.info(
            "Policy check 5 failed: MERCHANT_NOT_ALLOWED "
            "agent_id=%d merchant_id=%d",
            agent.id, merchant.id,
        )
        return PolicyDecision.block(
            RejectionReason.MERCHANT_NOT_ALLOWED,
            failed_at="check_5_merchant_allowlisted",
            **base,
        )

    # ── Check 6: Per-transaction limit ─────────────────────────────────
    if ctx.amount > agent.per_transaction_limit:
        logger.info(
            "Policy check 6 failed: PER_TX_LIMIT_EXCEEDED "
            "agent_id=%d amount=%.2f limit=%.2f",
            agent.id, ctx.amount, agent.per_transaction_limit,
        )
        return PolicyDecision.block(
            RejectionReason.PER_TX_LIMIT_EXCEEDED,
            failed_at="check_6_per_tx_limit",
            per_transaction_limit=agent.per_transaction_limit,
            **base,
        )

    # ── Check 7: Daily spend limit ─────────────────────────────────────
    spent_today: float = await ctx.get_daily_spend(agent.id)
    projected = spent_today + ctx.amount
    if projected > agent.daily_limit:
        logger.info(
            "Policy check 7 failed: DAILY_LIMIT_EXCEEDED "
            "agent_id=%d spent_today=%.2f amount=%.2f projected=%.2f limit=%.2f",
            agent.id, spent_today, ctx.amount, projected, agent.daily_limit,
        )
        return PolicyDecision.block(
            RejectionReason.DAILY_LIMIT_EXCEEDED,
            failed_at="check_7_daily_limit",
            spent_today=spent_today,
            daily_limit=agent.daily_limit,
            **base,
        )

    # ── Check 8: Rate limit (requests / minute) ────────────────────────
    rate = await ctx.count_recent_requests(agent.id, ctx.request_timestamp)
    if rate >= agent.max_requests_per_minute:
        logger.info(
            "Policy check 8 failed: RATE_LIMIT_EXCEEDED "
            "agent_id=%d rate=%d max=%d",
            agent.id, rate, agent.max_requests_per_minute,
        )
        return PolicyDecision.block(
            RejectionReason.RATE_LIMIT_EXCEEDED,
            failed_at="check_8_rate_limit",
            current_rate=rate,
            max_rate=agent.max_requests_per_minute,
            **base,
        )

    # ── Check 9: Duplicate request_id ──────────────────────────────────
    if await ctx.is_duplicate_request_id(ctx.request_id):
        logger.info(
            "Policy check 9 failed: DUPLICATE_REQUEST request_id=%s",
            ctx.request_id,
        )
        return PolicyDecision.block(
            RejectionReason.DUPLICATE_REQUEST,
            failed_at="check_9_duplicate_request_id",
            **base,
        )

    # ── Check 10: Sufficient balance ───────────────────────────────────
    if ctx.amount > agent.balance:
        logger.info(
            "Policy check 10 failed: INSUFFICIENT_BALANCE "
            "agent_id=%d amount=%.2f balance=%.2f",
            agent.id, ctx.amount, agent.balance,
        )
        return PolicyDecision.block(
            RejectionReason.INSUFFICIENT_BALANCE,
            failed_at="check_10_balance",
            balance=agent.balance,
            **base,
        )

    # ── All checks passed ──────────────────────────────────────────────
    logger.info(
        "Policy APPROVED: agent_id=%d merchant_id=%d amount=%.2f request=%s",
        agent.id, merchant.id, ctx.amount, ctx.request_id,
    )
    return PolicyDecision.approve(**base)
