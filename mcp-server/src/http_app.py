"""HTTP entrypoint for MCP server with health and manifest endpoints."""

from __future__ import annotations

import contextlib
import base64
import json
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import Resource as MCPResource
import mcp.types as mcp_types
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp.server.transport_security import TransportSecuritySettings

from .config import settings
from .tools.integrations import trigger_integration_tool
from .tools.tasks import create_task_tool, list_tasks_tool, update_task_status_tool
from .utils.logging import get_logger, setup_logging
from .auth.oauth_routes import router as oauth_router
from .auth.middleware import OAuthMiddleware

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


def _tool_annotations(read_only: bool, open_world: bool, destructive: bool) -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=read_only,
        openWorldHint=open_world,
        destructiveHint=destructive,
    )

def _tool_response(result: dict[str, Any], view: str) -> CallToolResult:
    message = result.get("message") or result.get("error") or "Request completed."
    data = result.get("data") or {}
    structured_content: dict[str, Any] = {
        "success": result.get("success", False),
        "message": message,
        "view": view,
        "payload": data,
    }

    if "count" in data and isinstance(data["count"], int):
        structured_content["count"] = data["count"]
    elif isinstance(data, dict) and isinstance(data.get("tasks"), list):
        structured_content["count"] = len(data["tasks"])
    if isinstance(data, dict) and "id" in data:
        structured_content["id"] = data["id"]
    if not structured_content["success"] and "error" in result:
        structured_content["error"] = result["error"]

    return CallToolResult(
        structuredContent=structured_content,
        content=[
            TextContent(
                type="text",
                text=message,
                meta={"ui": {"view": view, "payload": data}, "raw": result},
            )
        ],
    )


UI_TEMPLATE_URI = "ui://widget/tasks.html"


def _origin_from_base_url(base_url: str) -> str | None:
    if not base_url:
        return None
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _user_id_from_context(ctx: Context | None) -> str:
    if not ctx:
        return MOCK_USER_ID
    request = getattr(ctx.request_context, "request", None)
    if request and hasattr(request, "state"):
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return str(user_id)
    return MOCK_USER_ID


def _widget_meta() -> dict[str, Any]:
    origin = _origin_from_base_url(settings.public_base_url)
    connect_domains = [origin] if origin else []
    resource_domains = ["https://persistent.oaistatic.com"]
    return {
        "openai/widgetCSP": {
            "connect_domains": connect_domains,
            "resource_domains": resource_domains,
        },
        "openai/widgetDomain": "https://chatgpt.com",
        "openai/widgetDescription": "Shows task lists, status updates, and integration results.",
        "openai/widgetPrefersBorder": True,
    }


class WidgetFastMCP(FastMCP):
    async def list_resources(self) -> list[MCPResource]:
        resources = await super().list_resources()
        widget_meta = _widget_meta()
        updated: list[MCPResource] = []
        for resource in resources:
            if str(resource.uri) == UI_TEMPLATE_URI:
                updated.append(resource.model_copy(update={"meta": widget_meta}))
            else:
                updated.append(resource)
        return updated


def _register_widget_read_resource_handler(mcp: WidgetFastMCP) -> None:
    async def handler(req: mcp_types.ReadResourceRequest):
        context = mcp.get_context()
        resource = await mcp._resource_manager.get_resource(req.params.uri, context=context)
        content = await resource.read()
        meta = _widget_meta() if str(resource.uri) == UI_TEMPLATE_URI else None

        if isinstance(content, bytes):  # pragma: no cover
            blob = mcp_types.BlobResourceContents(
                uri=req.params.uri,
                blob=base64.b64encode(content).decode(),
                mimeType=resource.mime_type,
                meta=meta,
            )
            return mcp_types.ServerResult(mcp_types.ReadResourceResult(contents=[blob]))
        if not isinstance(content, str):
            content = json.dumps(content, default=str)

        text = mcp_types.TextResourceContents(
            uri=req.params.uri,
            text=content,
            mimeType=resource.mime_type,
            meta=meta,
        )
        return mcp_types.ServerResult(mcp_types.ReadResourceResult(contents=[text]))

    mcp._mcp_server.request_handlers[mcp_types.ReadResourceRequest] = handler


def create_app() -> FastAPI:
    allow_all_origins = settings.debug
    allowed_origins = ["*"] if allow_all_origins else settings.allowed_origins_list
    allowed_hosts: list[str] = []
    public_url = settings.public_base_url.strip()
    if public_url:
        parsed = urlparse(public_url)
        if parsed.hostname:
            if parsed.port:
                allowed_hosts.append(f"{parsed.hostname}:{parsed.port}")
            else:
                allowed_hosts.append(parsed.hostname)
    allowed_hosts.extend(settings.allowed_hosts_list)
    if settings.debug:
        allowed_hosts.extend(["localhost:*", "127.0.0.1:*", "[::1]:*"])

    mcp = WidgetFastMCP(
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
    _register_widget_read_resource_handler(mcp)

    @contextlib.asynccontextmanager
    async def _lifespan(_: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
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
        if allow_all_origins:
            return await call_next(request)
        path = request.url.path
        if path.startswith(("/login", "/authorize", "/.well-known/")):
            return await call_next(request)
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins_list:
            logger.warning(
                "Blocked request with disallowed origin",
                extra={"extra_fields": {"origin": origin, "path": request.url.path}},
            )
            return JSONResponse(status_code=403, content={"error": "Origin not allowed"})
        return await call_next(request)

    # Add OAuth middleware to protect MCP endpoints (if enabled)
    if settings.oauth_enabled:
        logger.info("OAuth authentication is ENABLED for MCP endpoints")
        app.middleware("http")(OAuthMiddleware(protected_paths=["/mcp"]))
    else:
        logger.warning("OAuth authentication is DISABLED - using mock user ID for all requests")

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

    @app.get(settings.openai_apps_verification_path)
    async def openai_domain_verification() -> Response:
        logger.info("OpenAI domain verification requested with token: %s", settings.openai_apps_verification_token)
        token = (settings.openai_apps_verification_token or "").strip()
        if not token:
            return Response(status_code=404)
        return Response(content=token, media_type="text/plain")

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
      const meta = window.openai?.toolResponseMetadata || {};
      let output = window.openai?.toolOutput || {};

      const tryParse = (value) => {
        if (typeof value !== "string") return value;
        try {
          return JSON.parse(value);
        } catch (err) {
          return value;
        }
      };

      output = tryParse(output);
      output.result = tryParse(output.result);

      const payload =
        output.payload ||
        output.data ||
        output.result?.payload ||
        output.result?.data ||
        meta.ui?.payload ||
        {};

      const tasks =
        payload.tasks ||
        output.tasks ||
        output.result?.tasks ||
        [];

      const message = output.message || payload.message || "Tasks";

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

    # TODO: Fix FastMCP list_resources decorator issue
    # @mcp.list_resources()
    # async def list_resources() -> list[dict[str, Any]]:
    #     return [
    #         {
    #             "uri": UI_TEMPLATE_URI,
    #             "name": "Tasks widget",
    #             "description": "Renders task lists, updates, and integration statuses.",
    #             "mimeType": "text/html+skybridge",
    #             "_meta": _widget_meta(),
    #         }
    #     ]

    @mcp.tool(
        name="create_task",
        title="Create Task",
        meta=_tool_meta(UI_TEMPLATE_URI, "Creating task…", "Task created."),
        annotations=_tool_annotations(read_only=False, open_world=False, destructive=False),
    )
    async def create_task(
        title: str,
        description: str | None = None,
        due_date: str | None = None,
        priority: Literal["low", "medium", "high"] = "medium",
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        user_id = _user_id_from_context(ctx)
        result = await create_task_tool(
            {
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority,
            },
            user_id,
        )
        return _tool_response(result, "task_card")

    @mcp.tool(
        name="list_tasks",
        title="List Tasks",
        meta=_tool_meta(UI_TEMPLATE_URI, "Fetching tasks…", "Tasks ready."),
        annotations=_tool_annotations(read_only=True, open_world=False, destructive=False),
    )
    async def list_tasks(
        status: Literal["pending", "in_progress", "completed"] | None = None,
        priority: Literal["low", "medium", "high"] | None = None,
        overdue: bool | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        user_id = _user_id_from_context(ctx)
        result = await list_tasks_tool(
            {"status": status, "priority": priority, "overdue": overdue},
            user_id,
        )
        return _tool_response(result, "task_table")

    @mcp.tool(
        name="update_task_status",
        title="Update Task Status",
        meta=_tool_meta(UI_TEMPLATE_URI, "Updating task…", "Task updated."),
        annotations=_tool_annotations(read_only=False, open_world=False, destructive=False),
    )
    async def update_task_status(
        task_id: str,
        status: Literal["pending", "in_progress", "completed"],
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        user_id = _user_id_from_context(ctx)
        result = await update_task_status_tool(
            {"task_id": task_id, "status": status},
            user_id,
        )
        return _tool_response(result, "task_card")

    @mcp.tool(
        name="trigger_integration",
        title="Trigger Integration",
        meta=_tool_meta(UI_TEMPLATE_URI, "Triggering integration…", "Integration triggered."),
        annotations=_tool_annotations(read_only=False, open_world=True, destructive=False),
    )
    async def trigger_integration(
        integration_type: Literal["jira", "email", "slack"],
        action: str,
        data: dict[str, Any] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        user_id = _user_id_from_context(ctx)
        result = await trigger_integration_tool(
            {
                "integration_type": integration_type,
                "action": action,
                "data": data or {},
            },
            user_id,
        )
        return _tool_response(result, "integration_status")

    @mcp.tool(
        name="generate_report",
        title="Generate Report",
        meta=_tool_meta(UI_TEMPLATE_URI, "Generating report…", "Report ready."),
        annotations=_tool_annotations(read_only=True, open_world=False, destructive=False),
    )
    async def generate_report(
        report_type: Literal["weekly", "monthly", "productivity"],
        format: Literal["json", "pdf", "csv"] | None = None,
        ctx: Context | None = None,
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
        annotations=_tool_annotations(read_only=False, open_world=False, destructive=False),
    )
    async def schedule_workflow(
        workflow_name: str,
        schedule: str | None = None,
        actions: list[dict[str, Any]] | None = None,
        ctx: Context | None = None,
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

    # Include OAuth routes
    app.include_router(oauth_router, tags=["oauth"])

    app.mount("/", mcp.streamable_http_app())
    return app
