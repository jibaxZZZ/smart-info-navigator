"""Tests for MCP tools - Task management and integrations.

These tests verify the business logic of MCP tools (NO AI/LLM calls).
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.tools.tasks import create_task_tool, list_tasks_tool, update_task_status_tool
from src.tools.integrations import trigger_integration_tool


# Mock user ID for testing
MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest_asyncio.fixture(autouse=True)
async def ensure_mock_user(mock_user):
    """Ensure the mock user exists for all tool tests."""
    return mock_user


class TestCreateTaskTool:
    """Test create_task MCP tool."""

    @pytest.mark.asyncio
    async def test_create_simple_task(self):
        """Test creating a simple task."""
        result = await create_task_tool(
            {"title": "Test Task", "priority": "high"}, MOCK_USER_ID
        )

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["title"] == "Test Task"
        assert result["data"]["priority"] == "high"
        assert result["data"]["status"] == "pending"
        assert "id" in result["data"]

    @pytest.mark.asyncio
    async def test_create_task_with_due_date(self):
        """Test creating a task with due date."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        result = await create_task_tool(
            {
                "title": "Task with Due Date",
                "description": "This task has a due date",
                "priority": "medium",
                "due_date": future_date,
            },
            MOCK_USER_ID,
        )

        assert result["success"] is True
        assert result["data"]["due_date"] is not None
        assert result["data"]["is_overdue"] is False

    @pytest.mark.asyncio
    async def test_create_task_invalid_due_date(self):
        """Test creating a task with invalid due date format."""
        result = await create_task_tool(
            {"title": "Invalid Date Task", "due_date": "invalid-date"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "Invalid due_date format" in result["error"]

    @pytest.mark.asyncio
    async def test_create_task_invalid_user(self):
        """Test creating a task with non-existent user."""
        fake_user_id = str(uuid4())

        result = await create_task_tool({"title": "Test Task"}, fake_user_id)

        assert result["success"] is False
        assert "User not found" in result["error"]


class TestListTasksTool:
    """Test list_tasks MCP tool."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_tasks(self):
        """Create test tasks before each test."""
        # Create a few tasks for testing
        pending = await create_task_tool(
            {"title": "Pending Task 1", "priority": "low"},
            MOCK_USER_ID,
        )
        in_progress = await create_task_tool(
            {"title": "In Progress Task", "priority": "high"},
            MOCK_USER_ID,
        )
        completed = await create_task_tool(
            {"title": "Completed Task", "priority": "medium"},
            MOCK_USER_ID,
        )

        await update_task_status_tool(
            {"task_id": in_progress["data"]["id"], "status": "in_progress"},
            MOCK_USER_ID,
        )
        await update_task_status_tool(
            {"task_id": completed["data"]["id"], "status": "completed"},
            MOCK_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_list_all_tasks(self):
        """Test listing all tasks."""
        result = await list_tasks_tool({}, MOCK_USER_ID)

        assert result["success"] is True
        assert result["data"]["count"] >= 3
        assert len(result["data"]["tasks"]) >= 3

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self):
        """Test filtering tasks by status."""
        result = await list_tasks_tool({"status": "pending"}, MOCK_USER_ID)

        assert result["success"] is True
        assert all(task["status"] == "pending" for task in result["data"]["tasks"])

    @pytest.mark.asyncio
    async def test_list_tasks_by_priority(self):
        """Test filtering tasks by priority."""
        result = await list_tasks_tool({"priority": "high"}, MOCK_USER_ID)

        assert result["success"] is True
        assert all(task["priority"] == "high" for task in result["data"]["tasks"])

    @pytest.mark.asyncio
    async def test_list_overdue_tasks(self):
        """Test filtering overdue tasks."""
        # Create an overdue task
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        await create_task_tool(
            {
                "title": "Overdue Task",
                "status": "pending",
                "priority": "high",
                "due_date": past_date,
            },
            MOCK_USER_ID,
        )

        result = await list_tasks_tool({"overdue": True}, MOCK_USER_ID)

        assert result["success"] is True
        # Should have at least the overdue task we just created
        assert result["data"]["count"] >= 1


class TestUpdateTaskStatusTool:
    """Test update_task_status MCP tool."""

    @pytest.mark.asyncio
    async def test_update_task_status_success(self):
        """Test successfully updating task status."""
        # Create a task first
        create_result = await create_task_tool(
            {"title": "Task to Update", "priority": "medium"}, MOCK_USER_ID
        )
        task_id = create_result["data"]["id"]

        # Update status
        result = await update_task_status_tool(
            {"task_id": task_id, "status": "completed"}, MOCK_USER_ID
        )

        assert result["success"] is True
        assert result["data"]["status"] == "completed"
        assert result["data"]["old_status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_task_invalid_status(self):
        """Test updating task with invalid status."""
        # Create a task first
        create_result = await create_task_tool(
            {"title": "Task to Update", "priority": "medium"}, MOCK_USER_ID
        )
        task_id = create_result["data"]["id"]

        # Try to update with invalid status
        result = await update_task_status_tool(
            {"task_id": task_id, "status": "invalid_status"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "Invalid status" in result["error"]

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test updating non-existent task."""
        fake_task_id = str(uuid4())

        result = await update_task_status_tool(
            {"task_id": fake_task_id, "status": "completed"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_update_task_invalid_uuid(self):
        """Test updating task with invalid UUID."""
        result = await update_task_status_tool(
            {"task_id": "not-a-uuid", "status": "completed"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "Invalid task_id format" in result["error"]


class TestTriggerIntegrationTool:
    """Test trigger_integration MCP tool."""

    @pytest.mark.asyncio
    async def test_email_integration_missing_credentials(self):
        """Test email integration when SMTP credentials not configured."""
        # This test assumes SMTP credentials are not set in test environment
        result = await trigger_integration_tool(
            {
                "integration_type": "email",
                "action": "send",
                "data": {
                    "to": "test@example.com",
                    "subject": "Test",
                    "body": "Test email",
                },
            },
            MOCK_USER_ID,
        )

        # Should fail gracefully with error message
        assert "error" in result or result.get("success") is False

    @pytest.mark.asyncio
    async def test_email_integration_task_notification(self):
        """Test email task notification format."""
        result = await trigger_integration_tool(
            {
                "integration_type": "email",
                "action": "task_notification",
                "data": {
                    "to": "test@example.com",
                    "task_title": "Test Task",
                    "task_status": "completed",
                    "task_id": "test-id",
                },
            },
            MOCK_USER_ID,
        )

        # May fail if SMTP not configured, but should handle gracefully
        assert "success" in result

    @pytest.mark.asyncio
    async def test_unsupported_integration_type(self):
        """Test unsupported integration type."""
        result = await trigger_integration_tool(
            {"integration_type": "unknown_service", "action": "test"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "Unknown integration type" in result["error"]

    @pytest.mark.asyncio
    async def test_jira_integration_not_implemented(self):
        """Test that Jira integration returns appropriate error."""
        result = await trigger_integration_tool(
            {"integration_type": "jira", "action": "create_issue"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "Phase 2" in result["error"]

    @pytest.mark.asyncio
    async def test_slack_integration_not_implemented(self):
        """Test that Slack integration returns appropriate error."""
        result = await trigger_integration_tool(
            {"integration_type": "slack", "action": "send_message"}, MOCK_USER_ID
        )

        assert result["success"] is False
        assert "Phase 2" in result["error"]
