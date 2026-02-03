"""Pytest configuration and fixtures."""

import os
import pytest

# Set test environment variables before importing app modules
os.environ["DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["JWT_SECRET_KEY"] = "test-secret-for-testing-only"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # Disable rate limiting in tests


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


class MockLLMProvider:
    """
    Mock LLM provider that returns predictable responses.
    Used in integration tests to avoid calling real LLM APIs.
    """

    async def generate(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str:
        last_user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_msg = msg["content"]
                break

        if "title" in last_user_msg.lower() and "summariz" in last_user_msg.lower():
            return "Test Chat Title"

        return f"Mock response to: {last_user_msg[:100]}"

    async def health_check(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _setup_database():
    """
    Set up an in-memory SQLite database with shared connection pool.

    Uses StaticPool so all async connections share the same in-memory database.
    Recreates tables for each test to ensure isolation.
    """
    import asyncio
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    import app.core.database as db_module
    from app.core.database import Base

    # Import models so Base.metadata knows about all tables
    from app.models.user import User  # noqa: F401
    from app.models.session import ChatSession, ChatMessage  # noqa: F401

    # Create engine with StaticPool (shared in-memory DB across connections)
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    test_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Patch the database module so the app uses our test engine
    original_engine = db_module.engine
    original_session_factory = db_module.AsyncSessionLocal

    db_module.engine = test_engine
    db_module.AsyncSessionLocal = test_session_factory

    # Create all tables
    async def _create():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_create())

    yield

    # Drop tables and restore originals
    async def _drop():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_drop())

    db_module.engine = original_engine
    db_module.AsyncSessionLocal = original_session_factory


@pytest.fixture
def mock_llm():
    """Patch the global LLM service to use a mock provider."""
    from app.services.llm.service import LLMService
    import app.services.llm.service as llm_module

    mock_service = LLMService(provider=MockLLMProvider())
    original = llm_module._llm_service
    llm_module._llm_service = mock_service
    yield mock_service
    llm_module._llm_service = original


@pytest.fixture
def client(mock_llm):
    """Create a test client with mocked LLM."""
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    """
    Create a test client that is already authenticated.
    Returns (client, user_data) tuple.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
            "name": "Test User",
        },
    )
    assert response.status_code == 200, f"Register failed: {response.json()}"
    user_data = response.json()["user"]
    return client, user_data
