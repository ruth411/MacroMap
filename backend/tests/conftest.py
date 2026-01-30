"""Pytest configuration and fixtures."""

import os
import pytest

# Set test environment variables before importing app modules
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-testing-only")


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"
