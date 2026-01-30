"""Tests for authentication service."""

import pytest


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_prepare_password_consistency(self):
        """Same password should produce same prepared hash."""
        from app.services.auth_service import _prepare_password
        password = "test_password_123"
        prepared1 = _prepare_password(password)
        prepared2 = _prepare_password(password)
        assert prepared1 == prepared2

    def test_prepare_password_different_passwords(self):
        """Different passwords should produce different prepared hashes."""
        from app.services.auth_service import _prepare_password
        prepared1 = _prepare_password("password1")
        prepared2 = _prepare_password("password2")
        assert prepared1 != prepared2

    def test_prepare_password_length(self):
        """Prepared password should be under bcrypt's 72 byte limit."""
        from app.services.auth_service import _prepare_password
        # Even very long passwords should be reduced to base64(SHA-256) = 44 chars
        long_password = "a" * 10000
        prepared = _prepare_password(long_password)
        assert len(prepared) < 72
        assert len(prepared) == 44  # Base64 encoded SHA-256


class TestJWT:
    """Tests for JWT token functionality."""

    def test_create_access_token(self):
        """Token creation should work."""
        from app.services.auth_service import AuthService
        user_id = "user-abc123"
        token = AuthService.create_access_token(user_id)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_verify_valid_token(self):
        """Valid token should verify and return user_id."""
        from app.services.auth_service import AuthService
        user_id = "user-abc123"
        token = AuthService.create_access_token(user_id)
        verified_user_id = AuthService.verify_token(token)
        assert verified_user_id == user_id

    def test_verify_invalid_token(self):
        """Invalid token should return None."""
        from app.services.auth_service import AuthService
        result = AuthService.verify_token("invalid.token.here")
        assert result is None

    def test_verify_tampered_token(self):
        """Tampered token should return None."""
        from app.services.auth_service import AuthService
        user_id = "user-abc123"
        token = AuthService.create_access_token(user_id)
        # Tamper with the token
        tampered = token[:-5] + "xxxxx"
        result = AuthService.verify_token(tampered)
        assert result is None

    def test_generate_user_id(self):
        """User ID generation should be unique."""
        from app.services.auth_service import AuthService
        id1 = AuthService.generate_user_id()
        id2 = AuthService.generate_user_id()
        assert id1 != id2
        assert id1.startswith("user-")
        assert id2.startswith("user-")
        assert len(id1) == 17  # "user-" + 12 hex chars
