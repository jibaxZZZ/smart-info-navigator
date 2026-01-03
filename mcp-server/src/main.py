"""Main entry point for Workflow Orchestrator MCP Server.

This server provides pure business logic tools for workflow orchestration.
NO AI/LLM calls are made from this server - only business operations.
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from .config import settings
from .utils.logging import setup_logging, get_logger

# Configure production-ready logging
setup_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    log_output=settings.log_output,
    log_file_path=settings.log_file_path,
    log_max_bytes=settings.log_max_bytes,
    log_backup_count=settings.log_backup_count,
)

logger = get_logger(__name__)


# Create MCP server instance
app = Server(settings.app_name)


@app.list_tools()
async def list_tools():
    """List available MCP tools for workflow orchestration."""
    return [
        {
            "name": "create_task",
            "description": "Create a new task in the system",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "due_date": {"type": "string", "description": "Due date (ISO format)"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["title"],
            },
        },
        {
            "name": "list_tasks",
            "description": "List tasks with optional filters",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "overdue": {"type": "boolean", "description": "Show only overdue tasks"},
                },
            },
        },
        {
            "name": "update_task_status",
            "description": "Update the status of a task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                },
                "required": ["task_id", "status"],
            },
        },
        {
            "name": "generate_report",
            "description": "Generate a business report from task data",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "report_type": {"type": "string", "enum": ["weekly", "monthly", "productivity"]},
                    "format": {"type": "string", "enum": ["json", "pdf", "csv"]},
                },
                "required": ["report_type"],
            },
        },
        {
            "name": "trigger_integration",
            "description": "Trigger an action in external systems (Jira, CRM, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "integration_type": {"type": "string", "enum": ["jira", "email", "slack"]},
                    "action": {"type": "string", "description": "Action to perform"},
                    "data": {"type": "object", "description": "Action payload"},
                },
                "required": ["integration_type", "action"],
            },
        },
        {
            "name": "schedule_workflow",
            "description": "Schedule a workflow to execute later or on trigger",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workflow_name": {"type": "string", "description": "Workflow identifier"},
                    "schedule": {"type": "string", "description": "Cron expression or ISO datetime"},
                    "actions": {"type": "array", "description": "Sequence of actions"},
                },
                "required": ["workflow_name", "actions"],
            },
        },
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """Route tool calls to appropriate handlers (business logic only, no AI)."""
    logger.info(
        f"MCP tool invoked: {name}",
        extra={"extra_fields": {"tool_name": name, "arguments": arguments}},
    )

    # TODO: Replace with actual OAuth user authentication in Phase 2
    # For now, use a mock user_id for testing
    mock_user_id = "00000000-0000-0000-0000-000000000001"

    # Tool implementations - All tools perform pure business logic, NO AI/LLM calls
    try:
        if name == "create_task":
            from .tools.tasks import create_task_tool

            result = await create_task_tool(arguments, mock_user_id)
            return [TextContent(type="text", text=str(result))]

        elif name == "list_tasks":
            from .tools.tasks import list_tasks_tool

            result = await list_tasks_tool(arguments, mock_user_id)
            return [TextContent(type="text", text=str(result))]

        elif name == "update_task_status":
            from .tools.tasks import update_task_status_tool

            result = await update_task_status_tool(arguments, mock_user_id)
            return [TextContent(type="text", text=str(result))]

        elif name == "trigger_integration":
            from .tools.integrations import trigger_integration_tool

            result = await trigger_integration_tool(arguments, mock_user_id)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_report":
            # Report generation - deferred to Phase 2
            logger.warning("Report generation not yet implemented")
            return [
                TextContent(
                    type="text",
                    text=str(
                        {
                            "success": False,
                            "error": "Report generation will be available in Phase 2",
                        }
                    ),
                )
            ]

        elif name == "schedule_workflow":
            # Workflow scheduling - deferred to Phase 2
            logger.warning("Workflow scheduling not yet implemented")
            return [
                TextContent(
                    type="text",
                    text=str(
                        {
                            "success": False,
                            "error": "Workflow scheduling will be available in Phase 2",
                        }
                    ),
                )
            ]

        else:
            logger.error(f"Unknown tool: {name}")
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=str(
                    {
                        "success": False,
                        "error": f"Tool execution failed: {str(e)}",
                    }
                ),
            )
        ]


async def main():
    """Run the MCP server."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
