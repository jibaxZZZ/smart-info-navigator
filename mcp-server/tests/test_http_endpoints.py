"""HTTP endpoint smoke tests for the MCP server."""

from fastapi.testclient import TestClient

from src.config import settings
from src.http_app import create_app


def test_health_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_manifest_endpoint() -> None:
    settings.public_base_url = "http://localhost:8000"

    with TestClient(create_app(), base_url="http://localhost:8000") as client:
        response = client.get("/manifest.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == settings.app_name
    assert payload["version"] == settings.app_version
    assert payload["mcp"]["transport"] == "streamable-http"
    assert payload["mcp"]["endpoint"] == "http://localhost:8000/mcp"
    assert payload["health"] == "/health"
    assert "list_tasks" in payload["tools"]


def test_mcp_initialize() -> None:
    settings.public_base_url = "http://localhost:8000"

    with TestClient(create_app(), base_url="http://localhost:8000") as client:
        response = client.post(
            "/mcp",
            headers={
                "content-type": "application/json",
                "accept": "application/json",
                "mcp-protocol-version": "2024-11-05",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0.0"},
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    assert payload["result"]["serverInfo"]["name"] == settings.app_name
