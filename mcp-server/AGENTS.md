# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the MCP server code.
- HTTP entrypoint: `src/http_main.py` (FastAPI + FastMCP).
- Stdio entrypoint: `src/main.py`.
- Core modules: `src/config.py` (configuration), `src/auth/` (OAuth + JWT + PKCE), `src/tools/` (MCP tool implementations), `src/services/` (business logic), `src/models/` (SQLAlchemy + Pydantic), `src/utils/` (shared utilities).
- `tests/` holds pytest suites.
- `alembic/` and `alembic.ini` are for migrations.
- Repo-level config: `pyproject.toml`, `uv.lock`, `.env.example`.

## Build, Test, and Development Commands
- `uv sync` — install dependencies.
- `uv run python -m src.http_main` — start HTTP MCP server.
- `uv run uvicorn src.http_main:app --reload --host 0.0.0.0 --port 8000` — hot reload.
- `uv run python -m src.main` — start MCP server over stdio.
- `uv run pytest` — run the test suite.
- `uv run mypy src/` — static type checking.
- `uv run black src/` — format code.
- `uv run ruff check src/` — linting.
- `uv run alembic upgrade head` — apply migrations.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, Black formatting, Ruff linting.
- Prefer async-first patterns; keep module boundaries clear (`tools` vs `services`).
- Filenames and module names are `snake_case`.

## Testing Guidelines
- Framework: `pytest` (see `tests/`).
- Test files are named `test_*.py`.
- Tests expect a local Postgres on port 5433 and Redis on 6380.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat:`, `fix:`, `docs:`).
- PRs should include: a brief summary, test results (or explicit skips), and any config/env changes.

## Security & Configuration Tips
- Never commit secrets. Use `.env` based on `.env.example`.
- OAuth is enabled via `OAUTH_ENABLED=true`.
- RSA keys for RS256 are local-only; do not commit key files.
