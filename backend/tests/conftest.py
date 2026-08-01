"""Shared test fixtures — in-memory FastAPI app with seeded owner.

Every test module can import these fixtures:
- ``client`` — httpx AsyncClient pointed at the FastAPI app
- ``auth_header`` — Authorization header with valid owner Bearer token
- ``owner_token`` — raw JWT string for the default owner
"""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.init_db import _seed_default_owner
from app.db.session import Base, get_session
from app.main import app


@pytest_asyncio.fixture
async def client():
    """Return an httpx AsyncClient pointed at the FastAPI app (in-memory SQLite)."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as s:
        await _seed_default_owner(s)
        await s.commit()

    async def override_get_session():
        async with async_session() as s:
            try:
                yield s
            finally:
                await s.close()

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def owner_token(client: AsyncClient) -> str:
    """Return a valid Bearer token for the default owner."""
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@agentpay.dev", "password": "admin123"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def auth_header(owner_token: str) -> dict[str, str]:
    """Return ``{'Authorization': 'Bearer <token>'}`` for the default owner."""
    return {"Authorization": f"Bearer {owner_token}"}


@pytest_asyncio.fixture
async def agent(client: AsyncClient, auth_header: dict[str, str]) -> dict:
    """Create and return an active, well-funded agent."""
    r = await client.post(
        "/api/v1/agents",
        json={
            "name": "TestAgent",
            "balance": 10_000.0,
            "per_transaction_limit": 1_000.0,
            "daily_limit": 5_000.0,
            "max_requests_per_minute": 10,
        },
        headers=auth_header,
    )
    assert r.status_code == 201, f"Create agent failed: {r.text}"
    return r.json()


@pytest_asyncio.fixture
async def merchant(client: AsyncClient, auth_header: dict[str, str]) -> dict:
    """Create and return an active merchant."""
    r = await client.post(
        "/api/v1/merchants",
        json={"display_name": "Test Merchant", "destination_reference": "m_test"},
        headers=auth_header,
    )
    assert r.status_code == 201, f"Create merchant failed: {r.text}"
    return r.json()


@pytest_asyncio.fixture
async def agent_with_allowlisted_merchant(
    client: AsyncClient, auth_header: dict[str, str], agent: dict, merchant: dict,
) -> tuple[dict, dict]:
    """Return (agent, merchant) with the merchant on the agent's allowlist."""
    r = await client.post(
        f"/api/v1/agents/{agent['id']}/allowlist",
        json={"merchant_id": merchant["id"]},
        headers=auth_header,
    )
    assert r.status_code == 201, f"Allowlist failed: {r.text}"
    return agent, merchant
