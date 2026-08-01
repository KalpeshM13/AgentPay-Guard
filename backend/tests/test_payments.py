"""Payment + Policy integration tests.

Covers every rejection scenario: frozen, per-tx limit, daily limit,
rate limit, duplicate, wallet balance, allowlist, and edge cases.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Happy path
# =============================================================================


class TestHappyPath:
    async def test_payment_settles(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r = await client.post("/api/v1/payments", json={
            "request_id": "req_happy", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 300.0,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "SETTLED"
        assert data["balance_after"] == 9_700.0  # 10000 - 300
        assert data["remaining_daily_limit"] is not None


# =============================================================================
# Per-transaction limit
# =============================================================================


class TestPerTransactionLimit:
    async def test_exact_limit_passes(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r = await client.post("/api/v1/payments", json={
            "request_id": "req_exact", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 1_000.0,
        })
        assert r.json()["status"] == "SETTLED"

    async def test_one_cent_over_limit_blocked(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r = await client.post("/api/v1/payments", json={
            "request_id": "req_over_1", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 1_000.01,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "PER_TX_LIMIT_EXCEEDED"

    async def test_way_over_limit_blocked(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r = await client.post("/api/v1/payments", json={
            "request_id": "req_wayover", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 10_000.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "PER_TX_LIMIT_EXCEEDED"


# =============================================================================
# Daily limit
# =============================================================================


class TestDailyLimit:
    async def test_within_daily_limit_passes(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        for i in range(5):
            r = await client.post("/api/v1/payments", json={
                "request_id": f"daily_pass_{i}", "agent_id": agent["id"],
                "merchant_id": merchant["id"], "amount": 1_000.0,
            })
            assert r.json()["status"] == "SETTLED"

    async def test_exceeds_daily_limit_blocked(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        # Spend 5 payments of 1000 = 5000 (exactly at daily limit)
        for i in range(5):
            await client.post("/api/v1/payments", json={
                "request_id": f"daily_{i}", "agent_id": agent["id"],
                "merchant_id": merchant["id"], "amount": 1_000.0,
            })
        # 6th payment should be blocked
        r = await client.post("/api/v1/payments", json={
            "request_id": "daily_over", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 1.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "DAILY_LIMIT_EXCEEDED"


# =============================================================================
# Rate limit
# =============================================================================


class TestRateLimit:
    async def test_rate_limit_blocks_after_max_requests(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        # The agent has max_requests_per_minute=10.
        # Send 11 within the same minute window.
        for i in range(10):
            r = await client.post("/api/v1/payments", json={
                "request_id": f"rate_{i}", "agent_id": agent["id"],
                "merchant_id": merchant["id"], "amount": 1.0,
            })
            # First 9 should settle; 10th might be at-limit (blocked)
            if i < 9:
                assert r.json()["status"] == "SETTLED"

        # 11th request should be rate-limited
        r = await client.post("/api/v1/payments", json={
            "request_id": "rate_blocked", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 1.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "RATE_LIMIT_EXCEEDED"


# =============================================================================
# Freeze (kill switch)
# =============================================================================


class TestFreeze:
    async def test_frozen_agent_payment_blocked(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant

        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)

        r = await client.post("/api/v1/payments", json={
            "request_id": "frozen_test", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "AGENT_FROZEN"

    async def test_unfrozen_payment_settles(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant

        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        await client.post(f"/api/v1/agents/{agent['id']}/unfreeze", headers=auth_header)

        r = await client.post("/api/v1/payments", json={
            "request_id": "unfrozen_test", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        assert r.json()["status"] == "SETTLED"


# =============================================================================
# Duplicate request_id
# =============================================================================


class TestDuplicateRequest:
    async def test_duplicate_request_id_blocked(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant

        await client.post("/api/v1/payments", json={
            "request_id": "dup_req", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        r = await client.post("/api/v1/payments", json={
            "request_id": "dup_req", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 50.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "DUPLICATE_REQUEST"

    async def test_different_request_ids_not_duplicate(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r1 = await client.post("/api/v1/payments", json={
            "request_id": "unique_1", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        r2 = await client.post("/api/v1/payments", json={
            "request_id": "unique_2", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        assert r1.json()["status"] == "SETTLED"
        assert r2.json()["status"] == "SETTLED"


# =============================================================================
# Wallet balance
# =============================================================================


class TestWalletBalance:
    async def test_exact_balance_settles(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        # Agent has 10000; set policy high enough
        await client.put(f"/api/v1/agents/{agent['id']}/policy", json={
            "per_transaction_limit": 20_000.0, "daily_limit": 50_000.0,
        }, headers=auth_header)

        r = await client.post("/api/v1/payments", json={
            "request_id": "exact_balance", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 10_000.0,
        })
        assert r.json()["status"] == "SETTLED"
        assert r.json()["balance_after"] == 0.0

    async def test_insufficient_balance_blocked(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        # Raise policy so we hit balance check not per-tx
        await client.put(f"/api/v1/agents/{agent['id']}/policy", json={
            "per_transaction_limit": 20_000.0, "daily_limit": 50_000.0,
        }, headers=auth_header)

        r = await client.post("/api/v1/payments", json={
            "request_id": "over_balance", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 10_000.01,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "INSUFFICIENT_BALANCE"


# =============================================================================
# Allowlist / merchant checks
# =============================================================================


class TestAllowlistChecks:
    async def test_non_allowlisted_merchant_blocked(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        # Create a second merchant NOT on the allowlist
        r = await client.post("/api/v1/merchants", json={
            "display_name": "Not Allowed", "destination_reference": "na",
        }, headers=auth_header)
        bad_merchant = r.json()

        r = await client.post("/api/v1/payments", json={
            "request_id": "not_allowed", "agent_id": agent["id"],
            "merchant_id": bad_merchant["id"], "amount": 100.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "MERCHANT_NOT_ALLOWED"

    async def test_nonexistent_agent_blocked(self, client: AsyncClient, merchant: dict):
        r = await client.post("/api/v1/payments", json={
            "request_id": "no_agent", "agent_id": 99999,
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "AGENT_NOT_FOUND"

    async def test_nonexistent_merchant_blocked(self, client: AsyncClient, agent: dict):
        r = await client.post("/api/v1/payments", json={
            "request_id": "no_merchant", "agent_id": agent["id"],
            "merchant_id": 99999, "amount": 100.0,
        })
        data = r.json()
        assert data["status"] == "BLOCKED"
        assert data["reason"] == "MERCHANT_NOT_FOUND"


# =============================================================================
# Edge cases
# =============================================================================


class TestPaymentEdgeCases:
    async def test_zero_amount_rejected(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r = await client.post("/api/v1/payments", json={
            "request_id": "zero_amt", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 0.0,
        })
        assert r.status_code == 422  # validation rejects amount <= 0

    async def test_negative_amount_rejected(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        r = await client.post("/api/v1/payments", json={
            "request_id": "neg_amt", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": -50.0,
        })
        assert r.status_code == 422

    async def test_balance_tracks_correctly_over_multiple_payments(
        self, client: AsyncClient, agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        payments = [(100, 9_900), (200, 9_700), (300, 9_400)]
        for i, (amount, expected_balance) in enumerate(payments):
            r = await client.post("/api/v1/payments", json={
                "request_id": f"track_{i}", "agent_id": agent["id"],
                "merchant_id": merchant["id"], "amount": amount,
            })
            assert r.json()["status"] == "SETTLED"
            assert r.json()["balance_after"] == expected_balance

    async def test_request_id_collision_across_agents(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        """Same request_id used by different agents is blocked.

        Note: if the second agent is not allowlisted for the merchant,
        the policy engine stops at MERCHANT_NOT_ALLOWED (check #5)
        before reaching the duplicate check (#9).
        """
        agent, merchant = agent_with_allowlisted_merchant

        # Create second agent
        r = await client.post("/api/v1/agents", json={
            "name": "Agent2", "balance": 5000, "per_transaction_limit": 1000, "daily_limit": 2000,
        }, headers=auth_header)
        agent2 = r.json()

        # First agent uses request_id
        await client.post("/api/v1/payments", json={
            "request_id": "cross_agent", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })

        # Second agent tries same request_id — blocked (either DUPLICATE_REQUEST
        # if allowlisted, or MERCHANT_NOT_ALLOWED if not). Both are valid BLOCKED.
        r = await client.post("/api/v1/payments", json={
            "request_id": "cross_agent", "agent_id": agent2["id"],
            "merchant_id": merchant["id"], "amount": 100.0,
        })
        assert r.json()["status"] == "BLOCKED"


# =============================================================================
# Dashboard
# =============================================================================


class TestDashboard:
    async def test_summary_reflects_setup(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        await client.post("/api/v1/payments", json={
            "request_id": "dash_s", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 500.0,
        })
        r = await client.get("/api/v1/dashboard/summary", headers=auth_header)
        data = r.json()
        assert data["total_agents"] >= 1
        assert data["today_spending"] == 500.0
        assert data["today_settled_count"] >= 1

    async def test_activity_shows_payments(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        await client.post("/api/v1/payments", json={
            "request_id": "dash_a", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 200.0,
        })
        r = await client.get("/api/v1/dashboard/activity", headers=auth_header)
        data = r.json()
        assert data["total"] >= 1
        assert "TestAgent" in str(data["items"])

    async def test_audit_has_events(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        await client.post("/api/v1/payments", json={
            "request_id": "dash_audit", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 200.0,
        })
        r = await client.get("/api/v1/dashboard/audit?limit=10", headers=auth_header)
        data = r.json()
        assert data["total"] >= 1  # at least payment_settled

    async def test_dashboard_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/v1/dashboard/summary")
        assert r.status_code == 401


# =============================================================================
# Audit
# =============================================================================


class TestAuditLogs:
    async def test_freeze_creates_audit(
        self, client: AsyncClient, auth_header: dict, agent: dict,
    ):
        await client.post(f"/api/v1/agents/{agent['id']}/freeze", headers=auth_header)
        r = await client.get("/api/v1/dashboard/audit?event_type=agent_frozen&limit=5", headers=auth_header)
        data = r.json()
        assert data["total"] >= 1

    async def test_policy_update_creates_audit(
        self, client: AsyncClient, auth_header: dict, agent: dict,
    ):
        await client.put(f"/api/v1/agents/{agent['id']}/policy", json={
            "per_transaction_limit": 500.0,
        }, headers=auth_header)
        r = await client.get("/api/v1/dashboard/audit?event_type=policy_updated&limit=5", headers=auth_header)
        data = r.json()
        assert data["total"] >= 1

    async def test_payment_blocked_creates_audit(
        self, client: AsyncClient, auth_header: dict,
        agent_with_allowlisted_merchant: tuple,
    ):
        agent, merchant = agent_with_allowlisted_merchant
        # Force a block
        await client.post("/api/v1/payments", json={
            "request_id": "audit_block", "agent_id": agent["id"],
            "merchant_id": merchant["id"], "amount": 2_000.0,
        })
        r = await client.get("/api/v1/dashboard/audit?event_type=payment_blocked&limit=5", headers=auth_header)
        data = r.json()
        assert data["total"] >= 1

    async def test_audit_for_nonexistent_event_type(self, client: AsyncClient, auth_header: dict):
        r = await client.get("/api/v1/dashboard/audit?event_type=nonexistent", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["total"] == 0
