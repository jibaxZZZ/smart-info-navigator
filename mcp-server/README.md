# Smart Info Navigator - MCP Server

Python MCP server for the Smart Info Navigator ChatGPT App. Provides OAuth 2.0 authentication (PKCE), deterministic task tools, and a streamable HTTP MCP endpoint.

## Tech Stack (versions from pyproject.toml)
- Python >= 3.11
- FastAPI >= 0.115
- Uvicorn >= 0.32
- SQLAlchemy (async) >= 2.0 + asyncpg >= 0.30
- Alembic >= 1.13 (migrations)
- PyJWT >= 2.10 (RS256/HS256)
- Redis >= 5.2
- pytest >= 9.0 + pytest-asyncio >= 0.24

## Entry Points
- HTTP MCP server: `src/http_main.py` (FastAPI + FastMCP)
- Stdio MCP server: `src/main.py`

## Local Setup

```bash
cd mcp-server
uv sync
cp .env.example .env
```

Edit `.env` and configure:
- `DATABASE_URL` (Postgres)
- `REDIS_URL`
- `OAUTH_ENABLED`
- `JWT_*` settings

## Run

HTTP server:
```bash
uv run python -m src.http_main
```

Hot reload (dev):
```bash
uv run uvicorn src.http_main:app --reload --host 0.0.0.0 --port 8000
```

Stdio MCP server:
```bash
uv run python -m src.main
```

## Migrations

Create a migration:
```bash
uv run alembic revision --autogenerate -m "describe change"
```

Apply migrations:
```bash
uv run alembic upgrade head
```

## OAuth 2.0 Flow (ChatGPT Apps)
Endpoints:
- `/.well-known/oauth-protected-resource` (protected resource metadata)
- `/.well-known/oauth-authorization-server` (authorization server metadata)
- `/authorize` (PKCE)
- `/token` (authorization_code + refresh_token)
- `/revoke`
- `/register` (dynamic client registration)

Demo login (App review):
- `DEMO_USERNAME` / `DEMO_PASSWORD` in `.env`
- OAuth `/authorize` shows a login page when demo credentials are enabled.

JWT signing:
- RS256 in production (RSA keys via `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH`)
- HS256 allowed for local dev

## MCP Tools
- `create_task`
- `list_tasks`
- `update_task_status`
- `trigger_integration` (email)

## Widget UI (ChatGPT Apps)
- Widgets are served via `ui://...` resources with `text/html+skybridge`.
- Each widget resource must include `openai/widgetCSP` and `openai/widgetDomain`.

## Postman
OAuth flow collection:
- `postman/oauth-flow.postman_collection.json`

MCP tools collection:
- `postman/smart-info-navigator.postman_collection.json`

## Tests

```bash
uv run pytest
```

## Project Layout
```
src/
  auth/           OAuth + JWT + PKCE
  tools/          MCP tool implementations
  services/       Business logic
  models/         SQLAlchemy + Pydantic models
  utils/          Logging and helpers
  http_app.py     FastAPI + FastMCP wiring
  http_main.py    HTTP entrypoint
```

## Notes
- No LLM calls are made on the backend.
- RSA key files are local-only and should not be committed.
