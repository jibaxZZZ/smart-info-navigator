"""PyTest configuration and shared fixtures for all tests."""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
import os

# Set test environment variables before importing app modules
# Using port 5433 to avoid conflict with local PostgreSQL on 5432
# For MVP, use same database as dev (tests will clean up after themselves)
os.environ["DATABASE_URL"] = "postgresql+asyncpg://workflow_user:workflow_password@localhost:5433/workflow_orchestrator"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["LOG_FORMAT"] = "text"
os.environ["LOG_OUTPUT"] = "stdout"
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("SMTP_PASSWORD", "")


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create test database schema once for all tests."""
    from src.database import init_db, close_db

    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Provide a clean database session for each test."""
    from src.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.execute(
            text("TRUNCATE TABLE task_audit_log, tasks, users RESTART IDENTITY CASCADE")
        )
        await session.commit()


@pytest_asyncio.fixture
async def mock_user(setup_database):
    """Ensure a mock user exists for tool tests."""
    from sqlalchemy import select
    from uuid import UUID
    from src.models.database import User
    from src.database import AsyncSessionLocal

    user_id = UUID("00000000-0000-0000-0000-000000000001")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id=user_id,
                oauth_sub="auth0|mock-user",
                email="mock@example.com",
                name="Mock User",
            )
            session.add(user)
            await session.commit()
        return user


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Additional test fixtures can be added here as needed
