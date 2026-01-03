"""Workflow data models."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, Any
from datetime import datetime


WorkflowStatus = Literal["scheduled", "running", "completed", "failed"]


class WorkflowAction(BaseModel):
    """A single action in a workflow."""

    tool_name: str = Field(..., description="MCP tool to execute")
    arguments: dict[str, Any] = Field(..., description="Tool arguments")
    order: int = Field(..., description="Execution order")


class Workflow(BaseModel):
    """A scheduled or recurring workflow."""

    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    actions: list[WorkflowAction] = Field(..., description="Sequence of actions")
    schedule: Optional[str] = Field(None, description="Cron expression or ISO datetime")
    status: WorkflowStatus = Field("scheduled", description="Workflow status")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )
    last_run: Optional[str] = Field(None, description="Last execution timestamp")
    next_run: Optional[str] = Field(None, description="Next scheduled execution")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "workflow_123",
                "name": "Daily Task Summary",
                "description": "Generate daily task summary and send via email",
                "actions": [
                    {"tool_name": "list_tasks", "arguments": {"status": "completed"}, "order": 1},
                    {"tool_name": "generate_report", "arguments": {"report_type": "daily"}, "order": 2},
                    {
                        "tool_name": "trigger_integration",
                        "arguments": {"integration_type": "email", "action": "send_report"},
                        "order": 3,
                    },
                ],
                "schedule": "0 9 * * *",
                "status": "scheduled",
                "created_at": "2026-01-03T12:00:00",
                "next_run": "2026-01-04T09:00:00",
            }
        }
    )
