"""End-to-end test: create agent → freeze → pay (blocked) → unfreeze →
update policy → pay again (policy in effect).

This test exercises the **complete** kill-switch + policy-update flow
through the live FastAPI stack (ASGI transport, in-memory SQLite).

Run with::

    pytest tests/test_e2e_freeze_policy.py -v -s
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import AuditEventType, RejectionReason
from app.db.init_db import _seed_default_owner
from app.db.session import Base, get_session
from app.main import app


# =============================================================================
# In-memory FastAPI test app
# =============================================================================


@pytest_asyncio.fixture
async def client():
    """Return an httpx AsyncClient pointed at the FastAPI app."""
    # -- In-memory SQLite engine (shared by all requests) --------------------
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # -- Seed the default owner account --------------------------------------
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await _seed_default_owner(s)
        await s.commit()

    # -- Override the get_session dependency to use our in-memory DB ----------
    async def override_get_session():
        async with async_session() as s:
            try:
                yield s
            finally:
                await s.close()

    app.dependency_overrides[get_session] = override_get_session

    # -- Build the test client -----------------------------------------------
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # -- Cleanup -------------------------------------------------------------
    app.dependency_overrides.clear()
    await engine.dispose()


# =============================================================================
# Login helper
# =============================================================================


async def login(client: AsyncClient) -> str:
    """Return a valid Bearer token for the default owner."""
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@agentpay.dev", "password": "admin123"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


# =============================================================================
# The single E2E test
# =============================================================================


@pytest.mark.asyncio
async def test_freeze_unfreeze_policy_update_flow(client: AsyncClient):
    """
    ┌─────────────────────────────────────────────────────────────────┐
    │  Stage 1 — Setup                                                │
    │    Create agent (balance=10k, per-tx=1k, daily=5k)             │
    │    Create merchant + allowlist                                  │
    │                                                                 │
    │  Stage 2 — Freeze                                               │
    │    POST /agents/1/freeze  →  FROZEN                             │
    │    Payment request        →  BLOCKED: AGENT_FROZEN              │
    │                                                                 │
    │  Stage 3 — Unfreeze                                             │
    │    POST /agents/1/unfreeze  →  ACTIVE                           │
    │    Payment request          →  SETTLED                          │
    │                                                                 │
    │  Stage 4 — Update policy                                        │
    │    PUT /agents/1/policy  (tighten per-tx to 200, daily to 300)  │
    │    Payment 150 → SETTLED (under both limits)                    │
    │    Payment 250 → BLOCKED: PER_TX_LIMIT_EXCEEDED                 │
    │                                                                 │
    │  Stage 5 — Audit verification                                   │
    │    agent_frozen, agent_unfrozen, policy_updated all present     │
    └─────────────────────────────────────────────────────────────────┘
    """

    token = await login(client)
    auth = {"Authorization": f"Bearer {token}"}

    # ── Stage 1: Setup ──────────────────────────────────────────────────

    # Create agent
    r = await client.post(
        "/api/v1/agents",
        json={
            "name": "HackathonAgent",
            "description": "Test agent for the hackathon demo.",
            "balance": 10_000.0,
            "per_transaction_limit": 1_000.0,
            "daily_limit": 5_000.0,
            "max_requests_per_minute": 10,
        },
        headers=auth,
    )
    assert r.status_code == 201, f"Create agent failed: {r.text}"
    agent = r.json()
    assert agent["status"] == "ACTIVE"
    assert agent["balance"] == 10_000.0

    # Create merchant
    r = await client.post(
        "/api/v1/merchants",
        json={
            "display_name": "Compute Provider",
            "destination_reference": "merchant_compute_01",
        },
        headers=auth,
    )
    assert r.status_code == 201, f"Create merchant failed: {r.text}"
    merchant = r.json()

    # Allowlist
    r = await client.post(
        f"/api/v1/agents/{agent['id']}/allowlist",
        json={"merchant_id": merchant["id"]},
        headers=auth,
    )
    assert r.status_code == 201, f"Allowlist failed: {r.text}"

    # ── Stage 2: Freeze (kill switch) ───────────────────────────────────

    # Freeze the agent
    r = await client.post(
        f"/api/v1/agents/{agent['id']}/freeze",
        headers=auth,
    )
    assert r.status_code == 200, f"Freeze failed: {r.text}"
    assert r.json()["status"] == "FROZEN"

    # Payment *must* be blocked
    r = await client.post(
        "/api/v1/payments",
        json={
            "request_id": "req_after_freeze",
            "agent_id": agent["id"],
            "merchant_id": merchant["id"],
            "amount": 100.0,
        },
    )
    assert r.status_code == 200
    payment = r.json()
    assert payment["status"] == "BLOCKED"
    assert payment["reason"] == RejectionReason.AGENT_FROZEN

    # ── Stage 3: Unfreeze ───────────────────────────────────────────────

    r = await client.post(
        f"/api/v1/agents/{agent['id']}/unfreeze",
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"

    # Payment should now settle
    r = await client.post(
        "/api/v1/payments",
        json={
            "request_id": "req_after_unfreeze",
            "agent_id": agent["id"],
            "merchant_id": merchant["id"],
            "amount": 100.0,
        },
    )
    assert r.status_code == 200
    payment = r.json()
    assert payment["status"] == "SETTLED"
    assert payment["balance_after"] == 9_900.0  # 10000 - 100

    # ── Stage 4: Update policy (tighten limits) ─────────────────────────

    r = await client.put(
        f"/api/v1/agents/{agent['id']}/policy",
        json={
            "per_transaction_limit": 200.0,
            "daily_limit": 300.0,
        },
        headers=auth,
    )
    assert r.status_code == 200, f"Policy update failed: {r.text}"
    policy = r.json()
    assert policy["per_transaction_limit"] == 200.0
    assert policy["daily_limit"] == 300.0
    assert policy["max_requests_per_minute"] == 10  # unchanged

    # Max single tx is now 200, max daily is now 300.
    # Spent so far today: 100 (from the unfreeze payment).
    # So 150 should pass: under per-tx (150 <= 200), under daily (100+150=250 <= 300)
    r = await client.post(
        "/api/v1/payments",
        json={
            "request_id": "req_under_new_policy",
            "agent_id": agent["id"],
            "merchant_id": merchant["id"],
            "amount": 150.0,
        },
    )
    assert r.status_code == 200
    payment = r.json()
    assert payment["status"] == "SETTLED", (
        f"Expected SETTLED (150 <= 200 per-tx, 100+150=250 <= 300 daily), got {payment}"
    )
    assert payment["balance_after"] == 9_750.0  # 9900 - 150

    # 250 exceeds the *new* per-tx limit of 200
    r = await client.post(
        "/api/v1/payments",
        json={
            "request_id": "req_over_new_per_tx",
            "agent_id": agent["id"],
            "merchant_id": merchant["id"],
            "amount": 250.0,
        },
    )
    assert r.status_code == 200
    payment = r.json()
    assert payment["status"] == "BLOCKED"
    assert payment["reason"] == RejectionReason.PER_TX_LIMIT_EXCEEDED

    # 60 would fit under per-tx (60 <= 200) but exceeds daily
    # (100+150+60=310 > 300)
    r = await client.post(
        "/api/v1/payments",
        json={
            "request_id": "req_over_daily",
            "agent_id": agent["id"],
            "merchant_id": merchant["id"],
            "amount": 60.0,
        },
    )
    assert r.status_code == 200
    payment = r.json()
    assert payment["status"] == "BLOCKED"
    assert payment["reason"] == RejectionReason.DAILY_LIMIT_EXCEEDED

    # ── Stage 5: Audit verification ─────────────────────────────────────

    r = await client.get("/api/v1/dashboard/audit?limit=100", headers=auth)
    assert r.status_code == 200
    audit = r.json()
    event_types = [e["event_type"] for e in audit["items"]]

    assert AuditEventType.AGENT_CREATED.value in event_types, (
        f"Missing agent_created in audit: {event_types}"
    )
    assert AuditEventType.AGENT_FROZEN.value in event_types, (
        f"Missing agent_frozen in audit: {event_types}"
    )
    assert AuditEventType.AGENT_UNFROZEN.value in event_types, (
        f"Missing agent_unfrozen in audit: {event_types}"
    )
    assert AuditEventType.POLICY_UPDATED.value in event_types, (
        f"Missing policy_updated in audit: {event_types}"
    )
    assert AuditEventType.PAYMENT_SETTLED.value in event_types, (
        f"Missing payment_settled in audit: {event_types}"
    )
    assert AuditEventType.PAYMENT_BLOCKED.value in event_types, (
        f"Missing payment_blocked in audit: {event_types}"
    )
