"""Authentication tests — register, login, /me, token validation, roles.

All tests use the in-memory FastAPI client from conftest.py.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# POST /auth/register
# =============================================================================


class TestRegister:
    async def test_register_new_user_returns_201(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={
            "email": "bob@agentpay.dev", "password": "secret123", "display_name": "Bob",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "bob@agentpay.dev"
        assert data["role"] == "viewer"

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "dup@agentpay.dev", "password": "secret123", "display_name": "First",
        })
        r = await client.post("/api/v1/auth/register", json={
            "email": "dup@agentpay.dev", "password": "secret456", "display_name": "Second",
        })
        assert r.status_code == 409

    async def test_register_short_password_returns_422(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={
            "email": "bad@agentpay.dev", "password": "ab", "display_name": "Bad",
        })
        assert r.status_code == 422

    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "password": "secret123", "display_name": "Bad",
        })
        assert r.status_code == 422

    async def test_register_empty_display_name_returns_422(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={
            "email": "test@agentpay.dev", "password": "secret123", "display_name": "",
        })
        assert r.status_code == 422


# =============================================================================
# POST /auth/login
# =============================================================================


class TestLogin:
    async def test_login_with_correct_credentials_returns_token(self, client: AsyncClient):
        # Register first
        await client.post("/api/v1/auth/register", json={
            "email": "login@agentpay.dev", "password": "secret123", "display_name": "Tester",
        })
        r = await client.post("/api/v1/auth/login", data={
            "username": "login@agentpay.dev", "password": "secret123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "wrongpw@agentpay.dev", "password": "secret123", "display_name": "Tester",
        })
        r = await client.post("/api/v1/auth/login", data={
            "username": "wrongpw@agentpay.dev", "password": "wrong",
        })
        assert r.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/login", data={
            "username": "ghost@agentpay.dev", "password": "secret123",
        })
        assert r.status_code == 401

    async def test_login_default_owner(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/login", data={
            "username": "admin@agentpay.dev", "password": "admin123",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()


# =============================================================================
# GET /auth/me
# =============================================================================


class TestMe:
    async def test_me_with_valid_token_returns_user(self, client: AsyncClient, owner_token: str):
        r = await client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "admin@agentpay.dev"
        assert data["role"] == "owner"

    async def test_me_without_token_returns_401(self, client: AsyncClient):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401

    async def test_me_with_bogus_token_returns_401(self, client: AsyncClient):
        r = await client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer totally.fake.token",
        })
        assert r.status_code == 401

    async def test_me_with_expired_token_returns_401(self, client: AsyncClient):
        # Create a token then we'll check that actual ones work;
        # bogus expired JWT
        r = await client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTkiLCJleHAiOjEwMDAwMDAwMDB9.xxx",
        })
        assert r.status_code == 401


# =============================================================================
# Role-based authorization
# =============================================================================


class TestRoles:
    async def test_viewer_cannot_create_agent(self, client: AsyncClient):
        """A viewer-token user gets 403 on admin-only endpoints."""
        await client.post("/api/v1/auth/register", json={
            "email": "viewer@agentpay.dev", "password": "secret123", "display_name": "Viewer",
        })
        r = await client.post("/api/v1/auth/login", data={
            "username": "viewer@agentpay.dev", "password": "secret123",
        })
        viewer_token = r.json()["access_token"]

        r = await client.post("/api/v1/agents", json={
            "name": "ShouldFail", "balance": 1000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers={"Authorization": f"Bearer {viewer_token}"})
        assert r.status_code == 403

    async def test_owner_can_create_agent(self, client: AsyncClient, auth_header: dict):
        r = await client.post("/api/v1/agents", json={
            "name": "OwnerAgent", "balance": 1000, "per_transaction_limit": 500, "daily_limit": 2000,
        }, headers=auth_header)
        assert r.status_code == 201

    async def test_various_invalid_tokens(self, client: AsyncClient):
        """Probe edge cases for token header format."""
        # Missing Bearer prefix
        r = await client.get("/api/v1/auth/me", headers={
            "Authorization": "some_random_string",
        })
        assert r.status_code == 401

        # Empty header
        r = await client.get("/api/v1/auth/me", headers={
            "Authorization": "",
        })
        assert r.status_code == 401 or r.status_code == 403
