"""Auth endpoint tests."""
from __future__ import annotations

import uuid

import pytest


class TestAuthEndpoints:
    """Tests for /api/v1/auth/* endpoints."""

    @pytest.mark.asyncio
    async def test_register_with_email(self, client):
        """Test user registration with email and password."""
        response = await client.post("/api/v1/auth/register", json={
            "email": f"user_{uuid.uuid4().hex[:8]}@fashionai.com",
            "password": "SecurePassword123!",
            "display_name": "Test User",
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["display_name"] == "Test User"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        """Test that duplicate email registration returns 409."""
        email = f"dup_{uuid.uuid4().hex[:8]}@fashionai.com"
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePassword123!",
        })
        response = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePassword123!",
        })
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_without_email_or_phone(self, client):
        """Test that registration without email or phone returns 400."""
        response = await client.post("/api/v1/auth/register", json={
            "password": "SecurePassword123!",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login returns tokens."""
        email = f"login_{uuid.uuid4().hex[:8]}@fashionai.com"
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePassword123!",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "SecurePassword123!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        """Test login with wrong password returns 401."""
        email = f"wrong_{uuid.uuid4().hex[:8]}@fashionai.com"
        await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePassword123!",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "WrongPassword",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me(self, authenticated_client):
        """Test getting current user profile."""
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client):
        """Test that /me without token returns 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data
