"""
Integration tests for MacroMap API.

Tests the full request lifecycle: auth flow, chat with mocked LLM,
session management, cookie-based auth, and guest vs authenticated behavior.
"""

import pytest


# ---------------------------------------------------------------------------
# Auth Flow: register → cookie → /me → login → logout
# ---------------------------------------------------------------------------
class TestAuthFlow:
    """End-to-end tests for the authentication lifecycle."""

    def test_register_sets_cookie(self, client):
        """Register should set an httpOnly auth cookie."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie_test@example.com",
                "password": "password123",
                "name": "Cookie Tester",
            },
        )
        assert response.status_code == 200

        data = response.json()
        # Token should NOT be in the JSON body (it's in the cookie now)
        assert "access_token" not in data
        # User info should be returned
        assert data["user"]["email"] == "cookie_test@example.com"
        assert data["user"]["name"] == "Cookie Tester"

        # Verify cookie was set
        assert "access_token" in client.cookies

    def test_register_then_me(self, client):
        """After register, /auth/me should work using the cookie."""
        # Register (cookie set automatically by TestClient)
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "me_test@example.com",
                "password": "password123",
            },
        )

        # /me should return user info (cookie sent automatically)
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "me_test@example.com"

    def test_login_sets_cookie(self, client):
        """Login should set an httpOnly auth cookie."""
        # First register
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login_test@example.com",
                "password": "password123",
            },
        )

        # Clear cookies to simulate a new browser session
        client.cookies.clear()

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "login_test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        assert "access_token" not in response.json()
        assert "access_token" in client.cookies

    def test_login_wrong_password(self, client):
        """Login with wrong password should return 401."""
        # Register
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong_pw@example.com",
                "password": "correct_password",
            },
        )
        client.cookies.clear()

        # Try wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong_pw@example.com",
                "password": "wrong_password",
            },
        )
        assert response.status_code == 401

    def test_logout_clears_cookie(self, client):
        """Logout should clear the auth cookie."""
        # Register (sets cookie)
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout_test@example.com",
                "password": "password123",
            },
        )
        assert "access_token" in client.cookies

        # Logout
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # /me should now fail
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_register_duplicate_email(self, client):
        """Registering with an existing email should fail."""
        payload = {
            "email": "dupe@example.com",
            "password": "password123",
        }
        # First registration succeeds
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 200

        # Second registration should fail
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_short_password(self, client):
        """Registration with a short password should fail."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "abc"},
        )
        assert response.status_code == 400
        assert "at least 6" in response.json()["detail"].lower()

    def test_me_without_auth(self, client):
        """/me without authentication should return 401."""
        client.cookies.clear()
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Chat Flow: guest mode and authenticated mode
# ---------------------------------------------------------------------------
class TestChatFlow:
    """End-to-end tests for the chat endpoint."""

    def test_guest_chat(self, client):
        """Guest users can chat without authentication."""
        client.cookies.clear()

        response = client.post(
            "/api/v1/chat/",
            json={
                "message": "What are Apple's risk factors?",
                "session_id": "guest-session-1",
                "use_rag": False,
                "use_templates": False,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert data["session_id"] == "guest-session-1"
        assert "Mock response to:" in data["response"]
        assert data["sources_used"] == 0

    def test_guest_chat_multi_turn(self, client):
        """Guest users can have multi-turn conversations."""
        client.cookies.clear()
        session_id = "guest-multi-turn"

        # First message
        r1 = client.post(
            "/api/v1/chat/",
            json={
                "message": "Hello",
                "session_id": session_id,
                "use_rag": False,
                "use_templates": False,
            },
        )
        assert r1.status_code == 200

        # Second message (same session)
        r2 = client.post(
            "/api/v1/chat/",
            json={
                "message": "Follow up question",
                "session_id": session_id,
                "use_rag": False,
                "use_templates": False,
            },
        )
        assert r2.status_code == 200
        assert r2.json()["session_id"] == session_id

    def test_authenticated_chat(self, auth_client):
        """Authenticated users get persisted messages."""
        client, user = auth_client

        # Create a session first
        session_resp = client.post(
            "/api/v1/chat/sessions",
            json={"title": "Test Session"},
        )
        assert session_resp.status_code == 200
        session_id = session_resp.json()["id"]

        # Send a chat message
        response = client.post(
            "/api/v1/chat/",
            json={
                "message": "What is Apple's revenue?",
                "session_id": session_id,
                "use_rag": False,
                "use_templates": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Mock response to:" in data["response"]

        # Verify the message was persisted by fetching the session
        session_detail = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert session_detail.status_code == 200
        messages = session_detail.json()["messages"]

        # Should have 2 messages: user + assistant
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is Apple's revenue?"
        assert messages[1]["role"] == "assistant"
        assert "Mock response to:" in messages[1]["content"]

    def test_chat_with_templates(self, client):
        """Chat with templates enabled should detect question type."""
        client.cookies.clear()

        response = client.post(
            "/api/v1/chat/",
            json={
                "message": "What are the main risk factors?",
                "session_id": "template-test",
                "use_rag": False,
                "use_templates": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # question_type should be detected
        assert data["question_type"] is not None

    def test_chat_empty_message(self, client):
        """Chat with empty message should fail validation."""
        response = client.post(
            "/api/v1/chat/",
            json={
                "message": "",
                "session_id": "empty-test",
            },
        )
        assert response.status_code == 422

    def test_chat_health(self, client):
        """Chat health endpoint should return provider status."""
        response = client.get("/api/v1/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "llm"
        assert data["healthy"] is True

    def test_clear_conversation(self, client):
        """Clearing a conversation should succeed."""
        response = client.post(
            "/api/v1/chat/clear",
            json={"session_id": "session-to-clear"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"


# ---------------------------------------------------------------------------
# Session Management: CRUD operations (requires auth)
# ---------------------------------------------------------------------------
class TestSessionManagement:
    """End-to-end tests for session CRUD operations."""

    def test_create_session(self, auth_client):
        """Authenticated users can create sessions."""
        client, user = auth_client

        response = client.post(
            "/api/v1/chat/sessions",
            json={"title": "My Analysis Session"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "My Analysis Session"
        assert "id" in data
        assert "created_at" in data

    def test_list_sessions(self, auth_client):
        """Authenticated users can list their sessions."""
        client, user = auth_client

        # Create two sessions
        client.post("/api/v1/chat/sessions", json={"title": "Session 1"})
        client.post("/api/v1/chat/sessions", json={"title": "Session 2"})

        # List sessions
        response = client.get("/api/v1/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["sessions"]) >= 2

    def test_get_session_detail(self, auth_client):
        """Can retrieve a specific session with messages."""
        client, user = auth_client

        # Create session
        session_resp = client.post(
            "/api/v1/chat/sessions",
            json={"title": "Detail Test"},
        )
        session_id = session_resp.json()["id"]

        # Get detail
        response = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["title"] == "Detail Test"
        assert "messages" in data

    def test_delete_session(self, auth_client):
        """Authenticated users can delete their sessions."""
        client, user = auth_client

        # Create session
        session_resp = client.post(
            "/api/v1/chat/sessions",
            json={"title": "To Delete"},
        )
        session_id = session_resp.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 200

        # Verify it's gone
        response = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 404

    def test_sessions_require_auth(self, client):
        """Session endpoints should require authentication."""
        client.cookies.clear()

        response = client.get("/api/v1/chat/sessions")
        assert response.status_code == 401

        response = client.post(
            "/api/v1/chat/sessions",
            json={"title": "Should Fail"},
        )
        assert response.status_code == 401

    def test_cannot_access_other_users_session(self, client):
        """A user cannot access another user's session."""
        # Register user A
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user_a@example.com",
                "password": "password123",
            },
        )
        # Create a session as user A
        session_resp = client.post(
            "/api/v1/chat/sessions",
            json={"title": "User A's Session"},
        )
        session_id = session_resp.json()["id"]

        # Logout user A, register user B
        client.post("/api/v1/auth/logout")
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user_b@example.com",
                "password": "password123",
            },
        )

        # User B should not see user A's session
        response = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Health & Misc Endpoints
# ---------------------------------------------------------------------------
class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    def test_health_check(self, client):
        """Health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "MacroMap"

    def test_root_endpoint(self, client):
        """Root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "docs" in data

    def test_retrieval_health(self, client):
        """Retrieval health check should work."""
        response = client.get("/api/v1/retrieval/health")
        assert response.status_code == 200
        assert response.json()["service"] == "retrieval"


# ---------------------------------------------------------------------------
# Bearer Header Fallback (API clients / testing compatibility)
# ---------------------------------------------------------------------------
class TestBearerFallback:
    """Verify that Bearer header auth still works as a fallback."""

    def test_bearer_header_auth(self, client):
        """API clients can still use Authorization: Bearer header."""
        from app.services.auth_service import AuthService

        # Register a user to get a valid user in the DB
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "bearer_test@example.com",
                "password": "password123",
            },
        )
        user_id = reg_resp.json()["user"]["id"]

        # Clear cookies so we're testing header-only auth
        client.cookies.clear()

        # Create a token manually
        token = AuthService.create_access_token(user_id)

        # Use Bearer header
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "bearer_test@example.com"
