"""HTTP entrypoint for MCP server with health and manifest endpoints."""

from __future__ import annotations

import contextlib
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .config import settings
from .tools.integrations import trigger_integration_tool
from .tools.tasks import create_task_tool, list_tasks_tool, update_task_status_tool
from .utils.logging import get_logger, setup_logging

setup_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    log_output=settings.log_output,
    log_file_path=settings.log_file_path,
    log_max_bytes=settings.log_max_bytes,
    log_backup_count=settings.log_backup_count,
)

logger = get_logger(__name__)


MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"


def _tool_meta(template_uri: str, invoking: str, invoked: str) -> dict[str, Any]:
    return {
        "openai/outputTemplate": template_uri,
        "openai/toolInvocation/invoking": invoking,
        "openai/toolInvocation/invoked": invoked,
        "openai/widgetAccessible": True,
    }


def _tool_response(result: dict[str, Any], view: str) -> dict[str, Any]:
    message = result.get("message") or result.get("error") or "Request completed."
    data = result.get("data") or {}
    structured_content: dict[str, Any] = {
        "success": result.get("success", False),
        "message": message,
        "view": view,
    }

    if "count" in data and isinstance(data["count"], int):
        structured_content["count"] = data["count"]
    elif isinstance(data, dict) and isinstance(data.get("tasks"), list):
        structured_content["count"] = len(data["tasks"])
    if isinstance(data, dict) and "id" in data:
        structured_content["id"] = data["id"]
    if not structured_content["success"] and "error" in result:
        structured_content["error"] = result["error"]

    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": message}],
        "_meta": {
            "ui": {"view": view, "payload": data},
            "raw": result,
        },
    }


UI_TEMPLATE_URI = "ui://widget/tasks.html"


def _origin_from_base_url(base_url: str) -> str | None:
    if not base_url:
        return None
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _widget_meta() -> dict[str, Any]:
    origin = _origin_from_base_url(settings.public_base_url)
    connect_domains = [origin] if origin else []
    resource_domains = [origin] if origin else []
    return {
        "openai/widgetCSP": {
            "connect_domains": connect_domains,
            "resource_domains": resource_domains,
        },
        "openai/widgetDescription": "Shows task lists, status updates, and integration results.",
        "openai/widgetPrefersBorder": True,
    }


def create_app() -> FastAPI:
    allowed_hosts: list[str] = []
    public_url = settings.public_base_url.strip()
    if public_url:
        parsed = urlparse(public_url)
        if parsed.hostname:
            if parsed.port:
                allowed_hosts.append(f"{parsed.hostname}:{parsed.port}")
            else:
                allowed_hosts.append(parsed.hostname)
    if settings.debug:
        allowed_hosts.extend(["localhost:*", "127.0.0.1:*", "[::1]:*"])

    mcp = FastMCP(
        settings.app_name,
        json_response=True,
        stateless_http=True,
        host="localhost" if settings.debug else "0.0.0.0",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=settings.allowed_origins_list,
        ),
    )

    @contextlib.asynccontextmanager
    async def _lifespan(_: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "authorization",
            "content-type",
        ],
        expose_headers=["mcp-session-id"],
    )

    @app.middleware("http")
    async def validate_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins_list:
            logger.warning(
                "Blocked request with disallowed origin",
                extra={"extra_fields": {"origin": origin, "path": request.url.path}},
            )
            return JSONResponse(status_code=403, content={"error": "Origin not allowed"})
        return await call_next(request)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/manifest.json")
    async def manifest() -> dict[str, Any]:
        base_url = settings.public_base_url.rstrip("/")
        endpoint = f"{base_url}/mcp" if base_url else "/mcp"
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "mcp": {
                "transport": "streamable-http",
                "endpoint": endpoint,
            },
            "health": "/health",
            "tools": [
                "create_task",
                "list_tasks",
                "update_task_status",
                "trigger_integration",
                "generate_report",
                "schedule_workflow",
            ],
        }

    @mcp.resource(UI_TEMPLATE_URI, mime_type="text/html+skybridge")
    def tasks_widget() -> str:
        return """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <style>
      body { font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; margin: 0; padding: 16px; }
      .summary { font-weight: 600; margin-bottom: 12px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e5e7eb; }
      .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; background: #eef2ff; }
      .empty { color: #6b7280; }
    </style>
  </head>
  <body>
    <div id=\"root\"></div>
    <script>
      const root = document.getElementById("root");
      const output = window.openai?.toolOutput || {};
      const meta = window.openai?.toolResponseMetadata || {};
      const payload = meta.ui?.payload || {};
      const tasks = payload.tasks || [];
      const message = output.message || "Tasks";

      root.innerHTML = "";
      const summary = document.createElement("div");
      summary.className = "summary";
      summary.textContent = message;
      root.appendChild(summary);

      if (!tasks.length) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "No tasks to display.";
        root.appendChild(empty);
      } else {
        const table = document.createElement("table");
        table.innerHTML = `
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Due</th>
            </tr>
          </thead>
          <tbody>
            ${tasks
              .map(
                (task) => `
              <tr>
                <td>${task.title}</td>
                <td><span class=\"badge\">${task.status}</span></td>
                <td>${task.priority || ""}</td>
                <td>${task.due_date || ""}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        `;
        root.appendChild(table);
      }
    </script>
  </body>
</html>
""".strip()

    @mcp.list_resources()
    async def list_resources() -> list[dict[str, Any]]:
        return [
            {
                "uri": UI_TEMPLATE_URI,
                "name": "Tasks widget",
                "description": "Renders task lists, updates, and integration statuses.",
                "mimeType": "text/html+skybridge",
                "_meta": _widget_meta(),
            }
        ]

    @mcp.tool(
        name="create_task",
        title="Create Task",
        meta=_tool_meta(UI_TEMPLATE_URI, "Creating task…", "Task created."),
    )
    async def create_task(
        title: str,
        description: str | None = None,
        due_date: str | None = None,
        priority: Literal["low", "medium", "high"] = "medium",
    ) -> dict[str, Any]:
        result = await create_task_tool(
            {
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority,
            },
            MOCK_USER_ID,
        )
        return _tool_response(result, "task_card")

    @mcp.tool(
        name="list_tasks",
        title="List Tasks",
        meta=_tool_meta(UI_TEMPLATE_URI, "Fetching tasks…", "Tasks ready."),
    )
    async def list_tasks(
        status: Literal["pending", "in_progress", "completed"] | None = None,
        priority: Literal["low", "medium", "high"] | None = None,
        overdue: bool | None = None,
    ) -> dict[str, Any]:
        result = await list_tasks_tool(
            {"status": status, "priority": priority, "overdue": overdue},
            MOCK_USER_ID,
        )
        return _tool_response(result, "task_table")

    @mcp.tool(
        name="update_task_status",
        title="Update Task Status",
        meta=_tool_meta(UI_TEMPLATE_URI, "Updating task…", "Task updated."),
    )
    async def update_task_status(
        task_id: str,
        status: Literal["pending", "in_progress", "completed"],
    ) -> dict[str, Any]:
        result = await update_task_status_tool(
            {"task_id": task_id, "status": status},
            MOCK_USER_ID,
        )
        return _tool_response(result, "task_card")

    @mcp.tool(
        name="trigger_integration",
        title="Trigger Integration",
        meta=_tool_meta(UI_TEMPLATE_URI, "Triggering integration…", "Integration triggered."),
    )
    async def trigger_integration(
        integration_type: Literal["jira", "email", "slack"],
        action: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = await trigger_integration_tool(
            {
                "integration_type": integration_type,
                "action": action,
                "data": data or {},
            },
            MOCK_USER_ID,
        )
        return _tool_response(result, "integration_status")

    @mcp.tool(
        name="generate_report",
        title="Generate Report",
        meta=_tool_meta(UI_TEMPLATE_URI, "Generating report…", "Report ready."),
    )
    async def generate_report(
        report_type: Literal["weekly", "monthly", "productivity"],
        format: Literal["json", "pdf", "csv"] | None = None,
    ) -> dict[str, Any]:
        return {
            "structuredContent": {
                "success": False,
                "message": "Report generation will be available in Phase 2",
            },
            "content": [
                {
                    "type": "text",
                    "text": "Report generation will be available in Phase 2",
                }
            ],
            "_meta": {"ui": {"view": "report_placeholder"}},
        }

    @mcp.tool(
        name="schedule_workflow",
        title="Schedule Workflow",
        meta=_tool_meta(UI_TEMPLATE_URI, "Scheduling workflow…", "Workflow scheduled."),
    )
    async def schedule_workflow(
        workflow_name: str,
        schedule: str | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "structuredContent": {
                "success": False,
                "message": "Workflow scheduling will be available in Phase 2",
            },
            "content": [
                {
                    "type": "text",
                    "text": "Workflow scheduling will be available in Phase 2",
                }
            ],
            "_meta": {"ui": {"view": "workflow_placeholder"}},
        }

    app.mount("/", mcp.streamable_http_app())
    return app


app = create_app()
