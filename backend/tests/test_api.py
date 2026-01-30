"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client."""
    from app.main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "docs" in data

    def test_debug_endpoint_removed(self, client):
        """Debug endpoint should not exist (security)."""
        response = client.get("/debug/env")
        assert response.status_code == 404


class TestRetrievalEndpoints:
    """Tests for retrieval API endpoints."""

    def test_retrieval_health(self, client):
        """Retrieval health check should work."""
        response = client.get("/api/v1/retrieval/health")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "retrieval"


class TestAuthValidation:
    """Tests for authentication input validation."""

    def test_register_missing_fields(self, client):
        """Registration with missing fields should fail."""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self, client):
        """Registration with invalid email should fail."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123"}
        )
        assert response.status_code == 422

    def test_register_password_required(self, client):
        """Registration without password should fail."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com"}  # Missing password
        )
        assert response.status_code == 422


class TestChatEndpoints:
    """Tests for chat API endpoints."""

    def test_chat_health(self, client):
        """Chat health check should work."""
        response = client.get("/api/v1/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "healthy" in data
