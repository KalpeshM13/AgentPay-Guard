"""Independent unit tests for the Payment Executor.

These tests use an **in-memory SQLite** database so the executor is tested
in complete isolation from the FastAPI server and any external dependencies.

Run with::

    pytest tests/test_payment_executor.py -v
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import AgentStatus, AuditEventType
from app.db.session import Base
from app.models.agent import Agent
from app.models.agent_merchant import AgentMerchant
from app.models.audit_log import AuditLog
from app.models.merchant import Merchant
from app.models.payment_request import PaymentRequest
from app.models.transaction import Transaction
from app.services.payment_executor import (
    count_recent_requests,
    execute,
    get_daily_spend,
    is_duplicate_request_id,
)


# =============================================================================
# In-memory test database
# =============================================================================


@pytest_asyncio.fixture
async def session():
    """Create a fresh in-memory SQLite database for every test."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def agent(session: AsyncSession):
    """A healthy, well-funded agent."""
    a = Agent(
        name="TestAgent",
        status=AgentStatus.ACTIVE,
        balance=10_000.0,
        per_transaction_limit=1_000.0,
        daily_limit=5_000.0,
        max_requests_per_minute=10,
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


@pytest_asyncio.fixture
async def agent_with_merchant(session: AsyncSession, agent: Agent):
    """An agent with an active allowlisted merchant."""
    m = Merchant(
        display_name="Test Merchant",
        destination_reference="merchant_test",
        active=True,
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)

    am = AgentMerchant(agent_id=agent.id, merchant_id=m.id)
    session.add(am)
    await session.commit()

    return agent, m


# =============================================================================
# execute() — happy path
# =============================================================================


@pytest_asyncio.fixture(autouse=True)
def _auto_use_asyncio():
    pass


@pytest.mark.asyncio
async def test_execute_debits_balance(session: AsyncSession, agent_with_merchant):
    """After execute(), the agent's balance is reduced by the amount."""
    agent, merchant = agent_with_merchant
    original = agent.balance

    tx = await execute(
        session=session,
        agent=agent,
        request_id="req_001",
        merchant_id=merchant.id,
        amount=300.0,
    )

    await session.refresh(agent)
    assert agent.balance == original - 300.0
    assert tx.amount == 300.0
    assert tx.balance_before == original
    assert tx.balance_after == agent.balance


@pytest.mark.asyncio
async def test_execute_creates_payment_request(session: AsyncSession, agent_with_merchant):
    """A PaymentRequest with status SETTLED is created."""
    agent, merchant = agent_with_merchant

    await execute(
        session=session, agent=agent,
        request_id="req_002", merchant_id=merchant.id, amount=200.0,
    )

    pr = (
        await session.execute(
            select(PaymentRequest).where(PaymentRequest.request_id == "req_002")
        )
    ).scalar_one()
    assert pr.status == "SETTLED"
    assert pr.amount == 200.0
    assert pr.reason is None


@pytest.mark.asyncio
async def test_execute_creates_transaction(session: AsyncSession, agent_with_merchant):
    """A Transaction ledger entry is created."""
    agent, merchant = agent_with_merchant

    tx = await execute(
        session=session, agent=agent,
        request_id="req_003", merchant_id=merchant.id, amount=150.0,
    )

    loaded = (
        await session.execute(select(Transaction).where(Transaction.id == tx.id))
    ).scalar_one()
    assert loaded.balance_before - loaded.amount == loaded.balance_after


@pytest.mark.asyncio
async def test_execute_creates_audit_log(session: AsyncSession, agent_with_merchant):
    """An AuditLog entry is written."""
    agent, merchant = agent_with_merchant

    await execute(
        session=session, agent=agent,
        request_id="req_004", merchant_id=merchant.id, amount=50.0,
    )

    logs = (await session.execute(select(AuditLog))).scalars().all()
    assert len(logs) >= 1
    latest = logs[-1]
    assert latest.event_type == AuditEventType.PAYMENT_SETTLED.value
    assert latest.actor == f"agent:{agent.id}"
    assert "req_004" in (latest.details or "")


# =============================================================================
# execute() — error paths
# =============================================================================


@pytest.mark.asyncio
async def test_execute_rejects_non_positive_amount(session: AsyncSession, agent_with_merchant):
    """Zero or negative amounts are rejected with ValueError."""
    agent, merchant = agent_with_merchant
    import pytest
    with pytest.raises(ValueError, match="positive"):
        await execute(
            session=session, agent=agent,
            request_id="req_z", merchant_id=merchant.id, amount=0.0,
        )
    with pytest.raises(ValueError, match="positive"):
        await execute(
            session=session, agent=agent,
            request_id="req_n", merchant_id=merchant.id, amount=-5.0,
        )


@pytest.mark.asyncio
async def test_execute_rejects_insufficient_balance(session: AsyncSession, agent_with_merchant):
    """If balance < amount, ValueError is raised (policy should have caught this)."""
    agent, merchant = agent_with_merchant
    agent.balance = 100.0
    import pytest
    with pytest.raises(ValueError, match="Insufficient balance"):
        await execute(
            session=session, agent=agent,
            request_id="req_over", merchant_id=merchant.id, amount=101.0,
        )


# =============================================================================
# Atomicity — the transaction must roll back on failure
# =============================================================================


@pytest.mark.asyncio
async def test_no_records_persisted_on_executor_failure(session: AsyncSession, agent_with_merchant):
    """If execute() raises, no PaymentRequests or Transactions are persisted."""
    agent, merchant = agent_with_merchant
    agent.balance = 50.0

    import pytest
    with pytest.raises(ValueError):
        await execute(
            session=session, agent=agent,
            request_id="req_rollback", merchant_id=merchant.id, amount=100.0,
        )

    # Nothing should be persisted
    prs = (await session.execute(select(PaymentRequest))).scalars().all()
    txs = (await session.execute(select(Transaction))).scalars().all()
    assert len(prs) == 0
    assert len(txs) == 0


# =============================================================================
# get_daily_spend()
# =============================================================================


@pytest.mark.asyncio
async def test_get_daily_spend_returns_zero_for_no_transactions(session: AsyncSession, agent):
    result = await get_daily_spend(session, agent.id)
    assert result == 0.0


@pytest.mark.asyncio
async def test_get_daily_spend_sums_todays_settled(session: AsyncSession, agent_with_merchant):
    agent, merchant = agent_with_merchant

    await execute(session=session, agent=agent, request_id="ds1", merchant_id=merchant.id, amount=200.0)
    await execute(session=session, agent=agent, request_id="ds2", merchant_id=merchant.id, amount=300.0)

    total = await get_daily_spend(session, agent.id)
    assert total == 500.0


# =============================================================================
# count_recent_requests()
# =============================================================================


@pytest.mark.asyncio
async def test_count_recent_requests_empty(session: AsyncSession, agent):
    from datetime import datetime, timezone
    count = await count_recent_requests(session, agent.id, datetime.now(timezone.utc))
    assert count == 0


# =============================================================================
# is_duplicate_request_id()
# =============================================================================


@pytest.mark.asyncio
async def test_is_duplicate_returns_false_for_new_id(session: AsyncSession):
    assert await is_duplicate_request_id(session, "never_seen") is False


@pytest.mark.asyncio
async def test_is_duplicate_returns_true_after_settled(session: AsyncSession, agent_with_merchant):
    agent, merchant = agent_with_merchant
    await execute(session=session, agent=agent, request_id="dup_test", merchant_id=merchant.id, amount=100.0)
    assert await is_duplicate_request_id(session, "dup_test") is True


# =============================================================================
# Multiple sequential payments
# =============================================================================


@pytest.mark.asyncio
async def test_multiple_sequential_payments(session: AsyncSession, agent_with_merchant):
    agent, merchant = agent_with_merchant
    original = agent.balance

    await execute(session=session, agent=agent, request_id="ms1", merchant_id=merchant.id, amount=100.0)
    await execute(session=session, agent=agent, request_id="ms2", merchant_id=merchant.id, amount=200.0)
    await execute(session=session, agent=agent, request_id="ms3", merchant_id=merchant.id, amount=300.0)

    await session.refresh(agent)
    assert agent.balance == original - 600.0

    txs = (await session.execute(select(Transaction))).scalars().all()
    assert len(txs) == 3
    assert sum(t.amount for t in txs) == 600.0

    requests = (await session.execute(select(PaymentRequest))).scalars().all()
    assert len(requests) == 3
    assert all(r.status == "SETTLED" for r in requests)

    logs = (await session.execute(select(AuditLog))).scalars().all()
    assert len(logs) == 3
    assert all(l.event_type == AuditEventType.PAYMENT_SETTLED.value for l in logs)
