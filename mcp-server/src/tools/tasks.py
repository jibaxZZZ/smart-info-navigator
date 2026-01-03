"""Task management MCP tools - Pure business logic, NO AI/LLM calls.

These tools provide CRUD operations for task management:
- create_task: Add a new task to the database
- list_tasks: Query tasks with filters
- update_task_status: Update task status and log audit trail
"""

from typing import Dict, Any
from datetime import datetime, timezone
from uuid import UUID
import json

from mcp.types import Tool, TextContent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import Task, TaskAuditLog, User
from ..database import AsyncSessionLocal
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def create_task_tool(arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a new task - pure business logic, NO AI.

    Args:
        arguments: Tool arguments containing task details
        user_id: Authenticated user ID

    Returns:
        MCP tool response with created task data

    Example:
        ```python
        result = await create_task_tool({
            "title": "Complete Q2 deliverables",
            "description": "Finalize all Q2 project deliverables",
            "priority": "high",
            "due_date": "2026-03-31T23:59:59Z"
        }, user_id="user-uuid")
        ```
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(
                f"Creating task for user {user_id}",
                extra={"extra_fields": {"user_id": user_id, "title": arguments.get("title")}},
            )

            # Validate user exists
            result = await db.execute(select(User).where(User.id == UUID(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                logger.error(f"User not found: {user_id}")
                return {
                    "success": False,
                    "error": f"User not found: {user_id}",
                }

            # Parse due date if provided
            due_date = None
            if arguments.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(arguments["due_date"].replace("Z", "+00:00"))
                except ValueError as e:
                    logger.error(f"Invalid due_date format: {e}")
                    return {
                        "success": False,
                        "error": f"Invalid due_date format. Use ISO format (e.g., '2026-03-31T23:59:59Z')",
                    }

            # Create task
            new_task = Task(
                user_id=UUID(user_id),
                title=arguments["title"],
                description=arguments.get("description"),
                priority=arguments.get("priority", "medium"),
                status="pending",
                due_date=due_date,
            )

            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)

            # Create audit log
            audit = TaskAuditLog(
                task_id=new_task.id,
                user_id=UUID(user_id),
                action="created",
                new_status="pending",
                extra_data=json.dumps({"title": new_task.title, "priority": new_task.priority}),
            )
            db.add(audit)
            await db.commit()

            logger.info(
                f"Task created successfully: {new_task.id}",
                extra={"extra_fields": {"task_id": str(new_task.id), "title": new_task.title}},
            )

            return {
                "success": True,
                "data": {
                    "id": str(new_task.id),
                    "title": new_task.title,
                    "description": new_task.description,
                    "status": new_task.status,
                    "priority": new_task.priority,
                    "due_date": new_task.due_date.isoformat() if new_task.due_date else None,
                    "created_at": new_task.created_at.isoformat(),
                    "is_overdue": new_task.is_overdue,
                },
                "message": f"✅ Task created: '{new_task.title}' (Priority: {new_task.priority})",
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating task: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to create task: {str(e)}",
            }


async def list_tasks_tool(arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List tasks with optional filters - pure business logic, NO AI.

    Args:
        arguments: Tool arguments containing filter criteria
        user_id: Authenticated user ID

    Returns:
        MCP tool response with list of tasks

    Example:
        ```python
        # List all pending tasks
        result = await list_tasks_tool({"status": "pending"}, user_id="user-uuid")

        # List overdue tasks
        result = await list_tasks_tool({"overdue": True}, user_id="user-uuid")
        ```
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(
                f"Listing tasks for user {user_id}",
                extra={"extra_fields": {"user_id": user_id, "filters": arguments}},
            )

            # Build query with filters
            query = select(Task).where(Task.user_id == UUID(user_id))

            # Apply filters
            if arguments.get("status"):
                query = query.where(Task.status == arguments["status"])

            if arguments.get("priority"):
                query = query.where(Task.priority == arguments["priority"])

            if arguments.get("overdue"):
                # Filter for overdue tasks (due_date < now AND status != completed)
                query = query.where(
                    Task.due_date < datetime.now(timezone.utc),
                    Task.status != "completed",
                )

            # Execute query
            result = await db.execute(query.order_by(Task.created_at.desc()))
            tasks = result.scalars().all()

            logger.info(
                f"Found {len(tasks)} tasks",
                extra={"extra_fields": {"count": len(tasks), "filters": arguments}},
            )

            # Format task data
            tasks_data = [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "is_overdue": task.is_overdue,
                }
                for task in tasks
            ]

            return {
                "success": True,
                "data": {
                    "tasks": tasks_data,
                    "count": len(tasks),
                    "filters_applied": arguments,
                },
                "message": f"Found {len(tasks)} task(s)",
            }

        except Exception as e:
            logger.error(f"Error listing tasks: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to list tasks: {str(e)}",
            }


async def update_task_status_tool(arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Update task status with audit logging - pure business logic, NO AI.

    Args:
        arguments: Tool arguments containing task_id and new status
        user_id: Authenticated user ID

    Returns:
        MCP tool response with updated task data

    Example:
        ```python
        result = await update_task_status_tool({
            "task_id": "task-uuid",
            "status": "completed"
        }, user_id="user-uuid")
        ```
    """
    async with AsyncSessionLocal() as db:
        try:
            task_id = UUID(arguments["task_id"])
            new_status = arguments["status"]

            logger.info(
                f"Updating task {task_id} status to {new_status}",
                extra={
                    "extra_fields": {
                        "task_id": str(task_id),
                        "new_status": new_status,
                        "user_id": user_id,
                    }
                },
            )

            # Get task
            result = await db.execute(
                select(Task).where(Task.id == task_id, Task.user_id == UUID(user_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task not found or access denied: {task_id}")
                return {
                    "success": False,
                    "error": f"Task not found or you don't have permission to update it",
                }

            # Validate status
            valid_statuses = ["pending", "in_progress", "completed"]
            if new_status not in valid_statuses:
                logger.error(f"Invalid status: {new_status}")
                return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                }

            # Store old status for audit log
            old_status = task.status

            # Update status
            task.status = new_status
            task.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(task)

            # Create audit log
            audit = TaskAuditLog(
                task_id=task.id,
                user_id=UUID(user_id),
                action="status_update",
                old_status=old_status,
                new_status=new_status,
                extra_data=json.dumps({"title": task.title}),
            )
            db.add(audit)
            await db.commit()

            logger.info(
                f"Task status updated: {old_status} → {new_status}",
                extra={
                    "extra_fields": {
                        "task_id": str(task.id),
                        "old_status": old_status,
                        "new_status": new_status,
                    }
                },
            )

            return {
                "success": True,
                "data": {
                    "id": str(task.id),
                    "title": task.title,
                    "status": task.status,
                    "old_status": old_status,
                    "updated_at": task.updated_at.isoformat(),
                },
                "message": f"✅ Task '{task.title}' updated: {old_status} → {new_status}",
            }

        except ValueError as e:
            logger.error(f"Invalid UUID format: {e}")
            return {
                "success": False,
                "error": f"Invalid task_id format",
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating task status: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update task status: {str(e)}",
            }
