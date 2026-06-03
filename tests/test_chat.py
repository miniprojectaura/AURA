"""Chat endpoint tests."""
from __future__ import annotations

import pytest


class TestChatEndpoints:
    """Tests for /api/v1/chat/* endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(self, authenticated_client):
        """Test creating a new chat session."""
        response = await authenticated_client.post("/api/v1/chat/sessions", json={
            "language": "en",
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["language"] == "en"
        assert data["message_count"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions(self, authenticated_client):
        """Test listing chat sessions."""
        # Create a session
        await authenticated_client.post("/api/v1/chat/sessions", json={"language": "en"})

        response = await authenticated_client.get("/api/v1/chat/sessions")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 1

    @pytest.mark.asyncio
    async def test_list_sessions_unauthenticated(self, client):
        """Test that listing sessions without token returns 401."""
        response = await client.get("/api/v1/chat/sessions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_classify_intent_design(self, authenticated_client):
        """Test intent classification for design request."""
        response = await authenticated_client.post("/api/v1/chat/classify", json={
            "text": "Design a red saree for my wedding",
        })
        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_classify_intent_greeting(self, authenticated_client):
        """Test intent classification for greeting."""
        response = await authenticated_client.post("/api/v1/chat/classify", json={
            "text": "Hello! How are you?",
        })
        assert response.status_code == 200
        data = response.json()
        assert "intent" in data


class TestWardrobeEndpoints:
    """Tests for /api/v1/wardrobe/* endpoints."""

    @pytest.mark.asyncio
    async def test_add_wardrobe_item(self, authenticated_client):
        """Test adding an item to the wardrobe."""
        response = await authenticated_client.post("/api/v1/wardrobe/", json={
            "name": "Blue Cotton Saree",
            "category": "saree",
            "color": "blue",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Blue Cotton Saree"
        assert data["category"] == "saree"

    @pytest.mark.asyncio
    async def test_list_wardrobe(self, authenticated_client):
        """Test listing wardrobe items."""
        # Add an item
        await authenticated_client.post("/api/v1/wardrobe/", json={
            "name": "Red Kurta",
            "category": "kurta",
            "color": "red",
        })

        response = await authenticated_client.get("/api/v1/wardrobe/")
        assert response.status_code == 200
        items = response.json()
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_delete_wardrobe_item(self, authenticated_client):
        """Test deleting a wardrobe item."""
        # Add an item
        create_response = await authenticated_client.post("/api/v1/wardrobe/", json={
            "name": "Old Shirt",
            "category": "shirt",
        })
        item_id = create_response.json()["id"]

        # Delete it
        response = await authenticated_client.delete(f"/api/v1/wardrobe/{item_id}")
        assert response.status_code == 204
