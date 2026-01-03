# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the MCP server code. Entry point: `src/main.py`.
- Core modules: `src/config.py` (configuration), `src/auth/` (OAuth), `src/tools/` (MCP tool implementations), `src/services/` (business logic), `src/models/` (Pydantic models), `src/utils/` (shared utilities).
- `tests/` holds pytest suites.
- `alembic/` and `alembic.ini` are for migrations (if/when database support is used).
- Repo-level config: `pyproject.toml`, `uv.lock`, `.env.example` (not committed here, but referenced in README).

## Build, Test, and Development Commands
- `uv sync` — install dependencies.
- `uv run python -m src.main` — start the MCP server over stdio.
- `uv run pytest` — run the test suite.
- `uv run mypy src/` — static type checking.
- `uv run black src/` — format code.
- `uv run ruff check src/` — linting.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, Black formatting, Ruff linting.
- Prefer async-first patterns where applicable; keep module boundaries clear (`tools` vs `services`).
- Filenames and module names are `snake_case`.

## Testing Guidelines
- Framework: `pytest` (see `tests/`).
- Test files are named `test_*.py`.
- Run tests with `uv run pytest`. Ensure Redis is running for local development.

## Commit & Pull Request Guidelines
- Git history currently contains only an “Initial commit”, so no strict convention is established.
- Use Conventional Commits if adding new history (e.g., `feat:`, `fix:`, `docs:`).
- PRs should include: a brief summary, test results (or explicit skips), and any config/env changes.

## Security & Configuration Tips
- Never commit secrets. Use `.env` based on `.env.example`.
- Validate any credentials via environment variables (e.g., `OPENAI_API_KEY`, `REDIS_URL`).
