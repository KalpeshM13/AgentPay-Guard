from datetime import datetime, timezone
import pytest
from app.models.agent import Agent
from app.models.merchant import Merchant
from app.core.constants import AgentStatus, RejectionReason
from app.services.policy_engine import PolicyContext, evaluate

async def dummy_daily_spend(agent_id: int) -> float:
    return 0.0

async def dummy_count_recent(agent_id: int, timestamp: datetime) -> int:
    return 0

async def dummy_is_duplicate(request_id: str) -> bool:
    return False

@pytest.fixture
def sample_agent():
    return Agent(
        id=1,
        owner_id=1,
        name="Test Agent",
        status=AgentStatus.ACTIVE,
        balance=1000.0,
        per_transaction_limit=50.0,
        daily_limit=200.0,
        max_requests_per_minute=10
    )

@pytest.fixture
def sample_merchant():
    return Merchant(
        id=1,
        name="AWS",
        destination_reference="0x123",
        active=True
    )

@pytest.mark.anyio
async def test_tc01_normal_payment_approved(sample_agent, sample_merchant):
    ctx = PolicyContext(
        request_id="req_tc01",
        request_timestamp=datetime.now(timezone.utc),
        agent=sample_agent,
        merchant=sample_merchant,
        is_merchant_allowlisted=True,
        amount=30.0,
        get_daily_spend=dummy_daily_spend,
        count_recent_requests=dummy_count_recent,
        is_duplicate_request_id=dummy_is_duplicate
    )
    decision = await evaluate(ctx)
    assert decision.approved is True
    assert decision.reason is None

@pytest.mark.anyio
async def test_tc02_per_tx_limit_violation(sample_agent, sample_merchant):
    ctx = PolicyContext(
        request_id="req_tc02",
        request_timestamp=datetime.now(timezone.utc),
        agent=sample_agent,
        merchant=sample_merchant,
        is_merchant_allowlisted=True,
        amount=75.0,  # exceeds per_tx_limit of 50.0
        get_daily_spend=dummy_daily_spend,
        count_recent_requests=dummy_count_recent,
        is_duplicate_request_id=dummy_is_duplicate
    )
    decision = await evaluate(ctx)
    assert decision.approved is False
    assert decision.reason == RejectionReason.PER_TX_LIMIT_EXCEEDED

@pytest.mark.anyio
async def test_tc03_daily_limit_exceeded(sample_agent, sample_merchant):
    async def high_daily_spend(agent_id: int) -> float:
        return 180.0  # 180 + 30 = 210 > daily_limit 200

    ctx = PolicyContext(
        request_id="req_tc03",
        request_timestamp=datetime.now(timezone.utc),
        agent=sample_agent,
        merchant=sample_merchant,
        is_merchant_allowlisted=True,
        amount=30.0,
        get_daily_spend=high_daily_spend,
        count_recent_requests=dummy_count_recent,
        is_duplicate_request_id=dummy_is_duplicate
    )
    decision = await evaluate(ctx)
    assert decision.approved is False
    assert decision.reason == RejectionReason.DAILY_LIMIT_EXCEEDED

@pytest.mark.anyio
async def test_tc04_unapproved_merchant(sample_agent, sample_merchant):
    ctx = PolicyContext(
        request_id="req_tc04",
        request_timestamp=datetime.now(timezone.utc),
        agent=sample_agent,
        merchant=sample_merchant,
        is_merchant_allowlisted=False,  # Not allowlisted
        amount=30.0,
        get_daily_spend=dummy_daily_spend,
        count_recent_requests=dummy_count_recent,
        is_duplicate_request_id=dummy_is_duplicate
    )
    decision = await evaluate(ctx)
    assert decision.approved is False
    assert decision.reason == RejectionReason.MERCHANT_NOT_ALLOWED

@pytest.mark.anyio
async def test_tc05_agent_frozen(sample_agent, sample_merchant):
    sample_agent.status = AgentStatus.FROZEN
    ctx = PolicyContext(
        request_id="req_tc05",
        request_timestamp=datetime.now(timezone.utc),
        agent=sample_agent,
        merchant=sample_merchant,
        is_merchant_allowlisted=True,
        amount=30.0,
        get_daily_spend=dummy_daily_spend,
        count_recent_requests=dummy_count_recent,
        is_duplicate_request_id=dummy_is_duplicate
    )
    decision = await evaluate(ctx)
    assert decision.approved is False
    assert decision.reason == RejectionReason.AGENT_FROZEN

@pytest.mark.anyio
async def test_tc06_replay_attack_duplicate(sample_agent, sample_merchant):
    async def duplicate_check(request_id: str) -> bool:
        return True

    ctx = PolicyContext(
        request_id="req_tc06_dup",
        request_timestamp=datetime.now(timezone.utc),
        agent=sample_agent,
        merchant=sample_merchant,
        is_merchant_allowlisted=True,
        amount=30.0,
        get_daily_spend=dummy_daily_spend,
        count_recent_requests=dummy_count_recent,
        is_duplicate_request_id=duplicate_check
    )
    decision = await evaluate(ctx)
    assert decision.approved is False
    assert decision.reason == RejectionReason.DUPLICATE_REQUEST
