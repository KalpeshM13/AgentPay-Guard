"""Payment Executor — the only component allowed to move money using Firestore.

The Executor **assumes policy approval has already been granted**.
It never re-checks policy rules.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.constants import AuditEventType
from app.models.audit_log import AuditLog
from app.models.payment_request import PaymentRequest
from app.models.transaction import Transaction

if TYPE_CHECKING:
    from app.models.agent import Agent

logger = logging.getLogger(__name__)


# =============================================================================
# Public API
# =============================================================================

async def execute(
    *,
    session: any,
    agent: Agent,
    request_id: str,
    merchant_id: int,
    amount: float,
) -> Transaction:
    """Execute an already-approved payment and update balance in Firestore."""
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if amount > agent.balance:
        raise ValueError(
            f"Insufficient balance: need {amount}, have {agent.balance}"
        )

    # Load and deduct from the user's balance
    user_id = getattr(agent, "user_id", None)
    if user_id is not None:
        user_data = await session.get("users", user_id)
        if user_data:
            user_balance = float(user_data.get("balance", 10.0))
            if amount > user_balance:
                raise ValueError(
                    f"Insufficient user balance: need {amount}, have {user_balance}"
                )
            user_data["balance"] = max(0.0, user_balance - amount)
            await session.update("users", user_id, user_data)

    balance_before = agent.balance
    agent.balance -= amount

    # Get auto-incrementing integer IDs atomically
    pr_id = await session.get_next_id("payment_requests")
    tx_id = await session.get_next_id("transactions")
    audit_id = await session.get_next_id("audit_events")

    # Create model objects
    payment_request = PaymentRequest(
        id=pr_id,
        request_id=request_id,
        agent_id=agent.id,
        user_id=user_id,
        merchant_id=merchant_id,
        amount=amount,
        status="SETTLED",
        reason=None,
        created_at=datetime.now(timezone.utc),
    )

    transaction = Transaction(
        id=tx_id,
        request_id=request_id,
        agent_id=agent.id,
        user_id=user_id,
        amount=amount,
        balance_before=balance_before,
        balance_after=agent.balance,
        settled_at=datetime.now(timezone.utc),
    )

    audit = AuditLog(
        id=audit_id,
        actor=f"agent:{agent.id}",
        event_type=AuditEventType.PAYMENT_SETTLED.value,
        user_id=user_id,
        details=json.dumps({
            "request_id": request_id,
            "agent_id": agent.id,
            "merchant_id": merchant_id,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": agent.balance,
        }),
        timestamp=datetime.now(timezone.utc),
    )

    # Persist all updates to Firestore
    await session.update("agents", agent.id, agent.to_dict())
    await session.insert("payment_requests", pr_id, payment_request.to_dict())
    await session.insert("transactions", tx_id, transaction.to_dict())
    await session.insert("audit_events", audit_id, audit.to_dict())

    logger.info(
        "Payment SETTLED: agent=%d merchant=%d amount=%.2f "
        "balance %.2f → %.2f request=%s tx_id=%d",
        agent.id, merchant_id, amount,
        balance_before, agent.balance,
        request_id, transaction.id,
    )

    return transaction


# =============================================================================
# Query helpers (used by the policy engine callbacks and dashboard)
# =============================================================================

async def get_daily_spend(session: any, agent_id: int) -> float:
    """Return the total SETTLED spend for *agent_id* on the current UTC day."""
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    
    # Query transactions for this agent
    tx_list = await session.query("transactions", [("agent_id", "==", agent_id)])
    
    # Filter locally to avoid index requirements
    total_spend = 0.0
    for tx in tx_list:
        settled_at = tx.get("settled_at")
        if settled_at:
            if hasattr(settled_at, "to_datetime"):
                settled_at_dt = settled_at.to_datetime()
            elif isinstance(settled_at, str):
                settled_at_dt = datetime.fromisoformat(settled_at.replace("Z", "+00:00"))
            else:
                settled_at_dt = settled_at
            
            if settled_at_dt >= today:
                total_spend += float(tx.get("amount", 0.0))
                
    return total_spend


async def count_recent_requests(
    session: any, agent_id: int, window_start: datetime,
) -> int:
    """Count payment requests since *window_start*."""
    # Query requests for this agent
    req_list = await session.query("payment_requests", [("agent_id", "==", agent_id)])
    
    # Filter locally
    count = 0
    for pr in req_list:
        created_at = pr.get("created_at")
        if created_at:
            if hasattr(created_at, "to_datetime"):
                created_at_dt = created_at.to_datetime()
            elif isinstance(created_at, str):
                created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_at_dt = created_at
                
            if created_at_dt >= window_start:
                count += 1
                
    return count


async def is_duplicate_request_id(
    session: any, request_id: str,
) -> bool:
    """Check whether *request_id* has already been used."""
    results = await session.query("payment_requests", [("request_id", "==", request_id)])
    return len(results) > 0
