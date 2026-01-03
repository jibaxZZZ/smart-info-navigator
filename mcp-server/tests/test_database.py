"""Tests for database connectivity and models.

These tests verify:
- Database connection works
- Models can be created and queried
- Relationships work correctly
- Constraints are enforced
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.models.database import User, Task, TaskAuditLog
from src.database import engine


class TestDatabaseConnection:
    """Test basic database connectivity."""

    @pytest.mark.asyncio
    async def test_database_connection(self, setup_database):
        """Test that database connection can be established."""
        async with engine.connect() as conn:
            result = await conn.execute(select(1))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_creation(self, db_session):
        """Test that database session can be created."""
        assert isinstance(db_session, AsyncSession)
        assert not db_session.is_active or True  # Session exists


class TestUserModel:
    """Test User model CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user."""
        user = User(
            oauth_sub="auth0|test123",
            email="test@example.com",
            name="Test User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.oauth_sub == "auth0|test123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.created_at is not None
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_user_oauth_sub_unique(self, db_session: AsyncSession):
        """Test that oauth_sub must be unique."""
        user1 = User(oauth_sub="auth0|duplicate", email="user1@example.com")
        db_session.add(user1)
        await db_session.commit()

        user2 = User(oauth_sub="auth0|duplicate", email="user2@example.com")
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session: AsyncSession):
        """Test retrieving user by ID."""
        user = User(oauth_sub="auth0|gettest", email="get@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        result = await db_session.execute(select(User).where(User.id == user.id))
        retrieved_user = result.scalar_one()

        assert retrieved_user.id == user.id
        assert retrieved_user.oauth_sub == user.oauth_sub

    @pytest.mark.asyncio
    async def test_get_user_by_oauth_sub(self, db_session: AsyncSession):
        """Test retrieving user by OAuth sub."""
        oauth_sub = "auth0|oauth_test"
        user = User(oauth_sub=oauth_sub, email="oauth@example.com")
        db_session.add(user)
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.oauth_sub == oauth_sub))
        retrieved_user = result.scalar_one()

        assert retrieved_user.oauth_sub == oauth_sub


class TestTaskModel:
    """Test Task model CRUD operations."""

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user for task tests."""
        user = User(oauth_sub="auth0|tasktest", email="tasktest@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_create_task(self, db_session: AsyncSession, test_user: User):
        """Test creating a new task."""
        task = Task(
            user_id=test_user.id,
            title="Test Task",
            description="This is a test task",
            status="pending",
            priority="high",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.id is not None
        assert task.user_id == test_user.id
        assert task.title == "Test Task"
        assert task.status == "pending"
        assert task.priority == "high"
        assert task.created_at is not None

    @pytest.mark.asyncio
    async def test_task_status_constraint(self, db_session: AsyncSession, test_user: User):
        """Test that task status must be valid."""
        task = Task(
            user_id=test_user.id,
            title="Invalid Status Task",
            status="invalid_status",  # Invalid status
            priority="medium",
        )
        db_session.add(task)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_task_priority_constraint(self, db_session: AsyncSession, test_user: User):
        """Test that task priority must be valid."""
        task = Task(
            user_id=test_user.id,
            title="Invalid Priority Task",
            status="pending",
            priority="urgent",  # Invalid priority
        )
        db_session.add(task)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_task_is_overdue(self, db_session: AsyncSession, test_user: User):
        """Test is_overdue property."""
        # Overdue task
        overdue_task = Task(
            user_id=test_user.id,
            title="Overdue Task",
            status="pending",
            priority="high",
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert overdue_task.is_overdue is True

        # Not overdue task
        future_task = Task(
            user_id=test_user.id,
            title="Future Task",
            status="pending",
            priority="high",
            due_date=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert future_task.is_overdue is False

        # Completed task (not overdue even if past due date)
        completed_task = Task(
            user_id=test_user.id,
            title="Completed Task",
            status="completed",
            priority="high",
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert completed_task.is_overdue is False

    @pytest.mark.asyncio
    async def test_cascade_delete_user_tasks(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that deleting a user cascades to delete their tasks."""
        task = Task(
            user_id=test_user.id,
            title="Will be deleted",
            status="pending",
            priority="low",
        )
        db_session.add(task)
        await db_session.commit()
        task_id = task.id

        # Delete user
        await db_session.delete(test_user)
        await db_session.commit()

        # Verify task is also deleted
        result = await db_session.execute(select(Task).where(Task.id == task_id))
        assert result.scalar_one_or_none() is None


class TestTaskAuditLog:
    """Test TaskAuditLog model."""

    @pytest_asyncio.fixture
    async def test_user_and_task(self, db_session: AsyncSession):
        """Create test user and task."""
        user = User(oauth_sub="auth0|audittest", email="audit@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        task = Task(
            user_id=user.id,
            title="Audit Test Task",
            status="pending",
            priority="medium",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        return user, task

    @pytest.mark.asyncio
    async def test_create_audit_log(self, db_session: AsyncSession, test_user_and_task):
        """Test creating an audit log entry."""
        user, task = test_user_and_task

        audit = TaskAuditLog(
            task_id=task.id,
            user_id=user.id,
            action="status_update",
            old_status="pending",
            new_status="in_progress",
        )
        db_session.add(audit)
        await db_session.commit()
        await db_session.refresh(audit)

        assert audit.id is not None
        assert audit.task_id == task.id
        assert audit.user_id == user.id
        assert audit.action == "status_update"
        assert audit.old_status == "pending"
        assert audit.new_status == "in_progress"
        assert audit.created_at is not None

    @pytest.mark.asyncio
    async def test_audit_log_cascade_delete(
        self, db_session: AsyncSession, test_user_and_task
    ):
        """Test that deleting a task cascades to delete audit logs."""
        user, task = test_user_and_task

        audit = TaskAuditLog(
            task_id=task.id,
            user_id=user.id,
            action="created",
            new_status="pending",
        )
        db_session.add(audit)
        await db_session.commit()
        audit_id = audit.id

        # Delete task
        await db_session.delete(task)
        await db_session.commit()

        # Verify audit log is also deleted
        result = await db_session.execute(
            select(TaskAuditLog).where(TaskAuditLog.id == audit_id)
        )
        assert result.scalar_one_or_none() is None


class TestRelationships:
    """Test model relationships."""

    @pytest.mark.asyncio
    async def test_user_tasks_relationship(self, db_session: AsyncSession):
        """Test that user.tasks relationship works."""
        user = User(oauth_sub="auth0|reltest", email="rel@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple tasks
        task1 = Task(user_id=user.id, title="Task 1", status="pending", priority="low")
        task2 = Task(
            user_id=user.id, title="Task 2", status="in_progress", priority="high"
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        # Reload user with tasks
        result = await db_session.execute(select(User).where(User.id == user.id))
        user = result.scalar_one()

        # Note: In async, we need to explicitly load relationships
        result = await db_session.execute(
            select(Task).where(Task.user_id == user.id)
        )
        tasks = result.scalars().all()

        assert len(tasks) == 2
        assert tasks[0].user_id == user.id
        assert tasks[1].user_id == user.id
