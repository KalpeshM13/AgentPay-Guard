"""CRUD tests — agents, merchants, allowlist endpoints.

All tests require authentication (conftest provides an owner token).
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Agents
# =============================================================================


class TestAgents:
    async def test_list_agents_empty(self, client: AsyncClient, auth_header: dict):
        r = await client.get("/api/v1/agents", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["agents"] == []

    async def test_create_agent(self, client: AsyncClient, auth_header: dict):
        r = await client.post("/api/v1/agents", json={
            "name": "Agent1", "balance": 5000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers=auth_header)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Agent1"
        assert data["status"] == "ACTIVE"
        assert data["balance"] == 5000.0

    async def test_create_agent_duplicate_name_409(self, client: AsyncClient, auth_header: dict):
        await client.post("/api/v1/agents", json={
            "name": "UniqueAgent", "balance": 1000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers=auth_header)
        r = await client.post("/api/v1/agents", json={
            "name": "UniqueAgent", "balance": 2000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers=auth_header)
        assert r.status_code == 409

    async def test_get_agent_by_id(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.get(f"/api/v1/agents/{agent['id']}", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["name"] == "TestAgent"

    async def test_get_agent_not_found(self, client: AsyncClient, auth_header: dict):
        r = await client.get("/api/v1/agents/99999", headers=auth_header)
        assert r.status_code == 404

    async def test_update_agent_name(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.put(f"/api/v1/agents/{agent['id']}", json={
            "name": "RenamedAgent",
        }, headers=auth_header)
        assert r.status_code == 200
        assert r.json()["name"] == "RenamedAgent"

    async def test_update_agent_balance(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.put(f"/api/v1/agents/{agent['id']}", json={
            "balance": 25_000.0,
        }, headers=auth_header)
        assert r.status_code == 200
        assert r.json()["balance"] == 25_000.0

    async def test_update_agent_to_duplicate_name_409(self, client: AsyncClient, auth_header: dict):
        # Create two agents, try to rename second to first's name
        await client.post("/api/v1/agents", json={
            "name": "FirstAgent", "balance": 1000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers=auth_header)
        r = await client.post("/api/v1/agents", json={
            "name": "SecondAgent", "balance": 1000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers=auth_header)
        second = r.json()
        r = await client.put(f"/api/v1/agents/{second['id']}", json={
            "name": "FirstAgent",
        }, headers=auth_header)
        assert r.status_code == 409

    async def test_delete_agent(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.delete(f"/api/v1/agents/{agent['id']}", headers=auth_header)
        assert r.status_code == 204
        # Verify deleted
        r = await client.get(f"/api/v1/agents/{agent['id']}", headers=auth_header)
        assert r.status_code == 404

    async def test_delete_nonexistent_agent_404(self, client: AsyncClient, auth_header: dict):
        r = await client.delete("/api/v1/agents/99999", headers=auth_header)
        assert r.status_code == 404

    async def test_list_agents_pagination(self, client: AsyncClient, auth_header: dict):
        # Create 3 agents
        for i in range(3):
            await client.post("/api/v1/agents", json={
                "name": f"PagAgent{i}", "balance": 1000, "per_transaction_limit": 500, "daily_limit": 2000,
            }, headers=auth_header)
        r = await client.get("/api/v1/agents?limit=2", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert len(data["agents"]) == 2

    async def test_list_agents_filter_by_status(self, client: AsyncClient, auth_header: dict, agent: dict):
        # Freeze one agent
        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        r = await client.get("/api/v1/agents?status=FROZEN", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert all(a["status"] == "FROZEN" for a in data["agents"])

    async def test_list_agents_filter_active(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.get("/api/v1/agents?status=ACTIVE", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert all(a["status"] == "ACTIVE" for a in data["agents"])


# =============================================================================
# Freeze / Unfreeze / Policy
# =============================================================================


class TestFreezeUnfreeze:
    async def test_freeze(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["status"] == "FROZEN"

    async def test_unfreeze(self, client: AsyncClient, auth_header: dict, agent: dict):
        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        r = await client.post(f"/api/v1/agents/{agent['id']}/unfreeze", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["status"] == "ACTIVE"

    async def test_freeze_already_frozen(self, client: AsyncClient, auth_header: dict, agent: dict):
        """Freezing an already-frozen agent should succeed (idempotent)."""
        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        r = await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["status"] == "FROZEN"

    async def test_freeze_nonexistent_404(self, client: AsyncClient, auth_header: dict):
        r = await client.post("/api/v1/agents/99999/freeze", headers=auth_header)
        assert r.status_code == 404

    async def test_policy_update(self, client: AsyncClient, auth_header: dict, agent: dict):
        r = await client.put(f"/api/v1/agents/{agent['id']}/policy", json={
            "per_transaction_limit": 200.0, "daily_limit": 300.0,
        }, headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert data["per_transaction_limit"] == 200.0
        assert data["daily_limit"] == 300.0
        assert data["max_requests_per_minute"] == 10  # unchanged

    async def test_policy_update_nonexistent_404(self, client: AsyncClient, auth_header: dict):
        r = await client.put("/api/v1/agents/99999/policy", json={
            "per_transaction_limit": 200.0,
        }, headers=auth_header)
        assert r.status_code == 404


# =============================================================================
# Merchants
# =============================================================================


class TestMerchants:
    async def test_create_merchant(self, client: AsyncClient, auth_header: dict):
        r = await client.post("/api/v1/merchants", json={
            "display_name": "New Merchant", "destination_reference": "m_ref",
        }, headers=auth_header)
        assert r.status_code == 201
        data = r.json()
        assert data["display_name"] == "New Merchant"
        assert data["active"] is True

    async def test_create_merchant_duplicate_409(self, client: AsyncClient, auth_header: dict):
        await client.post("/api/v1/merchants", json={
            "display_name": "Unique Merchant", "destination_reference": "m_ref1",
        }, headers=auth_header)
        r = await client.post("/api/v1/merchants", json={
            "display_name": "Unique Merchant", "destination_reference": "m_ref2",
        }, headers=auth_header)
        assert r.status_code == 409

    async def test_list_merchants(self, client: AsyncClient, auth_header: dict, merchant: dict):
        r = await client.get("/api/v1/merchants", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    async def test_list_merchants_active_only(self, client: AsyncClient, auth_header: dict, merchant: dict):
        r = await client.get("/api/v1/merchants?active_only=true", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert all(m["active"] for m in data["merchants"])

    async def test_delete_merchant(self, client: AsyncClient, auth_header: dict, merchant: dict):
        r = await client.delete(f"/api/v1/merchants/{merchant['id']}", headers=auth_header)
        assert r.status_code == 204

    async def test_delete_nonexistent_merchant_404(self, client: AsyncClient, auth_header: dict):
        r = await client.delete("/api/v1/merchants/99999", headers=auth_header)
        assert r.status_code == 404


# =============================================================================
# Allowlist
# =============================================================================


class TestAllowlist:
    async def test_add_to_allowlist(
        self, client: AsyncClient, auth_header: dict, agent: dict, merchant: dict,
    ):
        r = await client.post(
            f"/api/v1/agents/{agent['id']}/allowlist",
            json={"merchant_id": merchant["id"]},
            headers=auth_header,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["agent_id"] == agent["id"]
        assert data["merchant_id"] == merchant["id"]

    async def test_add_duplicate_to_allowlist_409(
        self, client: AsyncClient, auth_header: dict, agent: dict, merchant: dict,
    ):
        await client.post(f"/api/v1/agents/{agent['id']}/allowlist", json={
            "merchant_id": merchant["id"],
        }, headers=auth_header)
        r = await client.post(f"/api/v1/agents/{agent['id']}/allowlist", json={
            "merchant_id": merchant["id"],
        }, headers=auth_header)
        assert r.status_code == 409

    async def test_add_nonexistent_merchant_to_allowlist_404(
        self, client: AsyncClient, auth_header: dict, agent: dict,
    ):
        r = await client.post(f"/api/v1/agents/{agent['id']}/allowlist", json={
            "merchant_id": 99999,
        }, headers=auth_header)
        assert r.status_code == 404

    async def test_list_allowlist(self, client: AsyncClient, auth_header: dict, agent: dict, merchant: dict):
        await client.post(f"/api/v1/agents/{agent['id']}/allowlist", json={
            "merchant_id": merchant["id"],
        }, headers=auth_header)
        r = await client.get(f"/api/v1/agents/{agent['id']}/allowlist", headers=auth_header)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    async def test_remove_from_allowlist(
        self, client: AsyncClient, auth_header: dict, agent: dict, merchant: dict,
    ):
        await client.post(f"/api/v1/agents/{agent['id']}/allowlist", json={
            "merchant_id": merchant["id"],
        }, headers=auth_header)
        r = await client.delete(
            f"/api/v1/agents/{agent['id']}/allowlist/{merchant['id']}",
            headers=auth_header,
        )
        assert r.status_code == 204
        # Verify removed
        r = await client.get(f"/api/v1/agents/{agent['id']}/allowlist", headers=auth_header)
        assert r.json()["total"] == 0

    async def test_remove_nonexistent_allowlist_404(
        self, client: AsyncClient, auth_header: dict, agent: dict,
    ):
        r = await client.delete(
            f"/api/v1/agents/{agent['id']}/allowlist/99999",
            headers=auth_header,
        )
        assert r.status_code == 404

    async def test_allowlist_nonexistent_agent(self, client: AsyncClient, auth_header: dict):
        r = await client.post("/api/v1/agents/99999/allowlist", json={
            "merchant_id": 1,
        }, headers=auth_header)
        assert r.status_code == 404
