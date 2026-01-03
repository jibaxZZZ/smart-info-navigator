# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the React + TypeScript UI code.
- `src/components/` holds reusable UI components.
- `src/hooks/`, `src/stores/`, and `src/lib/` contain hooks, state management, and shared utilities.
- `src/types/` stores shared TypeScript types.
- `src/styles/` contains global styles and Tailwind setup.
- `public/` is for static assets, and `index.html` is the Vite entry shell.

## Build, Test, and Development Commands
Run these from `ui/`:
- `npm install` — install dependencies.
- `npm run dev` — start the Vite dev server.
- `npm run build` — typecheck (`tsc`) and build production assets.
- `npm run preview` — preview the production build locally.
- `npm run lint` — run ESLint with zero warnings allowed.
- `npm run type-check` — run TypeScript in no-emit mode.

## Coding Style & Naming Conventions
- TypeScript + React functional components; prefer hooks and small, focused components.
- Indentation uses 2 spaces; prefer single quotes in TS/TSX (match existing files).
- Tailwind utility classes for styling; keep reusable class logic in `src/lib/` helpers.
- Linting via ESLint; keep codebase lint-clean before PRs.

## Testing Guidelines
- No frontend test runner is configured yet. If you add one, update this guide and include a standard `npm run test` command.
- Keep components structured for easy unit testing (pure props in, render out).

## Commit & Pull Request Guidelines
- Prefer Conventional Commits (e.g., `feat:`, `fix:`, `chore:`).
- PRs should include a short summary, test/lint results (or explicit skips), and screenshots for any UI changes.

## Security & Configuration Tips
- Do not hard-code secrets. Use `.env` files and follow `.env.example` if present at repo root.
- The UI expects a backend API; when needed, run the MCP server via the repo root tooling or `docker-compose`.
