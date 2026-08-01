"""AI explainability tests — fallback mode (no API keys configured).

Tests that all AI endpoints work with deterministic fallback text
and verify the provider is 'fallback' in the response.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# POST /ai/explain-blocked
# =============================================================================


class TestExplainBlocked:
    async def test_explain_blocked_returns_200(self, client: AsyncClient, owner_token: str):
        r = await client.post(
            "/api/v1/ai/explain-blocked",
            json={
                "request_id": "req_x",
                "agent_name": "AgentX",
                "merchant_name": "MerchantX",
                "amount": 2_000.0,
                "reason": "PER_TX_LIMIT_EXCEEDED",
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["provider"] == "fallback"
        assert len(data["explanation"]) > 20

    async def test_all_rejection_reasons_have_fallback(
        self, client: AsyncClient, owner_token: str,
    ):
        reasons = [
            "AGENT_NOT_FOUND", "AGENT_FROZEN", "MERCHANT_NOT_FOUND",
            "MERCHANT_NOT_ACTIVE", "MERCHANT_NOT_ALLOWED",
            "PER_TX_LIMIT_EXCEEDED", "DAILY_LIMIT_EXCEEDED",
            "RATE_LIMIT_EXCEEDED", "DUPLICATE_REQUEST", "INSUFFICIENT_BALANCE",
        ]
        for reason in reasons:
            r = await client.post(
                "/api/v1/ai/explain-blocked",
                json={
                    "request_id": "x", "agent_name": "A", "merchant_name": "M",
                    "amount": 500.0, "reason": reason,
                },
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["provider"] == "fallback"
            assert len(data["explanation"]) > 10

    async def test_explain_blocked_unknown_reason_has_generic_fallback(
        self, client: AsyncClient, owner_token: str,
    ):
        r = await client.post(
            "/api/v1/ai/explain-blocked",
            json={
                "request_id": "x", "agent_name": "A", "merchant_name": "M",
                "amount": 500.0, "reason": "SOME_WEIRD_REASON",
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        assert "SOME_WEIRD_REASON" in r.json()["explanation"]


# =============================================================================
# POST /ai/explain-policy
# =============================================================================


class TestExplainPolicy:
    async def test_explain_policy_full(self, client: AsyncClient, owner_token: str):
        r = await client.post(
            "/api/v1/ai/explain-policy",
            json={
                "agent_name": "AgentX",
                "per_transaction_limit": 1_000.0,
                "daily_limit": 5_000.0,
                "max_requests_per_minute": 5,
                "balance": 10_000.0,
                "status": "ACTIVE",
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["provider"] == "fallback"
        assert "active" in data["explanation"].lower()

    async def test_explain_policy_partial(self, client: AsyncClient, owner_token: str):
        """Only some fields provided."""
        r = await client.post(
            "/api/v1/ai/explain-policy",
            json={"agent_name": "Minimal"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        assert r.json()["provider"] == "fallback"

    async def test_explain_policy_frozen(self, client: AsyncClient, owner_token: str):
        r = await client.post(
            "/api/v1/ai/explain-policy",
            json={
                "agent_name": "FrozenAgent",
                "status": "FROZEN",
                "per_transaction_limit": 500.0,
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        assert "frozen" in r.json()["explanation"].lower()


# =============================================================================
# GET /ai/summarize-audit
# =============================================================================


class TestSummarizeAudit:
    async def test_summarize_empty_audit(self, client: AsyncClient, owner_token: str):
        r = await client.get(
            "/api/v1/ai/summarize-audit?limit=10",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["provider"] == "fallback"
        assert "No audit events" in data["explanation"]

    async def test_summarize_with_events(
        self, client: AsyncClient, auth_header: dict, owner_token: str,
        agent: dict,
    ):
        # Create events: freeze + unfreeze
        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        await client.post(f"/api/v1/agents/{agent['id']}/unfreeze", headers=auth_header)

        r = await client.get(
            "/api/v1/ai/summarize-audit?limit=10",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["provider"] == "fallback"
        assert "payment" in data["explanation"].lower() or "event" in data["explanation"].lower()

    async def test_summarize_audit_filtered_by_agent(
        self, client: AsyncClient, auth_header: dict, owner_token: str,
        agent: dict,
    ):
        r = await client.get(
            f"/api/v1/ai/summarize-audit?agent_id={agent['id']}&limit=10",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 200
        assert r.json()["provider"] == "fallback"


# =============================================================================
# Auth / edge cases
# =============================================================================


class TestAIEdgeCases:
    async def test_all_endpoints_require_auth(self, client: AsyncClient):
        assert (await client.post("/api/v1/ai/explain-blocked", json={
            "request_id": "x", "agent_name": "A", "merchant_name": "M",
            "amount": 500.0, "reason": "AGENT_FROZEN",
        })).status_code == 401

        assert (await client.post("/api/v1/ai/explain-policy", json={
            "agent_name": "A",
        })).status_code == 401

        assert (await client.get("/api/v1/ai/summarize-audit")).status_code == 401

    async def test_explain_blocked_with_validation_error(self, client: AsyncClient, owner_token: str):
        r = await client.post(
            "/api/v1/ai/explain-blocked",
            json={},  # missing all fields
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 422

    async def test_explain_policy_with_validation_error(self, client: AsyncClient, owner_token: str):
        r = await client.post(
            "/api/v1/ai/explain-policy",
            json={},  # missing agent_name
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 422
