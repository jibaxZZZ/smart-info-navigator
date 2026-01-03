# Repository Guidelines

## Project Structure & Module Organization
- `mcp-server/` is the Python MCP server (business logic only, no AI/LLM calls). Core code lives in `mcp-server/src/` with tools in `mcp-server/src/tools/`, services in `mcp-server/src/services/`, and SQLAlchemy models in `mcp-server/src/models/`.
- `mcp-server/tests/` contains pytest suites for tools and database models.
- `ui/` is the Vite + React frontend. Source code lives in `ui/src/` and styles in `ui/src/styles/`.
- `docker/` and `docker-compose.yml` define local containers for PostgreSQL, Redis, the MCP server, and the UI.
- Project docs: `README.md`, `SETUP.md`, `MVP-SUMMARY.md`, `PORTS.md`.

## Build, Test, and Development Commands
Backend (from `mcp-server/`):
- `uv sync` — install dependencies.
- `uv run python -m src.main` — start MCP server (stdio).
- `uv run pytest` — run backend tests.
- `uv run mypy src/` — type checking.
- `uv run black src/` and `uv run ruff check src/` — formatting and linting.

Frontend (from `ui/`):
- `npm install` — install dependencies.
- `npm run dev` — start Vite dev server.
- `npm run build` — typecheck and build.
- `npm run lint` / `npm run type-check` — lint and typecheck.

Docker:
- `docker-compose up` — runs Postgres (5433), Redis (6380), MCP server (8000), UI (3000).

## Coding Style & Naming Conventions
- Python: async-first, SQLAlchemy 2.0 style, Pydantic models in `mcp-server/src/models/`. Format with Black; lint with Ruff. Use explicit logging via `mcp-server/src/utils/logging.py`.
- TypeScript/React: functional components, Tailwind utility classes, types in `ui/src/types/`. Use ESLint for linting.
- Secrets: never hard-code. Use `.env` files (see `.env.example`).

## Testing Guidelines
- Backend tests use `pytest` + `pytest-asyncio`. Test files live under `mcp-server/tests/` and are named `test_*.py`.
- Tests expect a running local Postgres on port 5433; see `mcp-server/tests/conftest.py`.

## Commit & Pull Request Guidelines
- Git history currently contains only the initial commit; no established convention yet. Prefer Conventional Commits (e.g., `feat:`, `fix:`) for new work.
- PRs should include: summary, test results (or explicit skips), and screenshots for UI changes.

## Security & Configuration Tips
- OAuth/Auth0 is deferred; `mcp-server/src/main.py` uses a mock user. Avoid assuming authenticated user context unless it’s implemented.
- Email integration uses Gmail SMTP; ensure `SMTP_*` variables are set before testing.
