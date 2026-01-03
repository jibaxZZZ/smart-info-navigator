"""Task data models for workflow orchestration."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


TaskStatus = Literal["pending", "in_progress", "completed"]
TaskPriority = Literal["low", "medium", "high"]


class Task(BaseModel):
    """A task in the workflow system."""

    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field("pending", description="Task status")
    priority: TaskPriority = Field("medium", description="Task priority")
    due_date: Optional[str] = Field(None, description="Due date (ISO format)")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last update timestamp",
    )
    assigned_to: Optional[str] = Field(None, description="User ID assigned to")
    tags: list[str] = Field(default_factory=list, description="Task tags")

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.status == "completed":
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            return due < datetime.now()
        except ValueError:
            return False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task_123",
                "title": "Complete Q2 deliverables",
                "description": "Finalize all Q2 project deliverables",
                "status": "in_progress",
                "priority": "high",
                "due_date": "2026-03-31T23:59:59",
                "created_at": "2026-01-03T12:00:00",
                "updated_at": "2026-01-03T13:00:00",
                "assigned_to": "user_456",
                "tags": ["q2", "deliverables"],
            }
        }
    )


class TaskFilter(BaseModel):
    """Filter options for listing tasks."""

    status: Optional[TaskStatus] = Field(None, description="Filter by status")
    priority: Optional[TaskPriority] = Field(None, description="Filter by priority")
    overdue: Optional[bool] = Field(None, description="Show only overdue tasks")
    assigned_to: Optional[str] = Field(None, description="Filter by assignee")
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
