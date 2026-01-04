# Smart Info Navigator UI

React + Vite frontend for the Smart Info Navigator ChatGPT App. This UI is used for local development, Storybook previews, and standalone browser testing. It talks to the MCP server over HTTP and renders task workflows with a deterministic, tool-driven UX (no backend LLM calls).

## Tech Stack (versions from package.json)
- React 18.3
- TypeScript 5.7
- Vite 6.0
- TanStack Query 5.62 (data fetching + cache)
- Zustand 5.0 (client state)
- Axios 1.7 (HTTP)
- Tailwind CSS 3.4 + tailwindcss-animate
- Radix UI primitives + shadcn/ui patterns
- Storybook 10.1 (component docs)

## Architecture Overview

### Data flow
- `src/lib/mcp-client.ts` wraps MCP HTTP calls.
- React Query hooks fetch and mutate via the MCP client.
- UI components are pure and consume typed props from MCP responses.

### Key folders
- `src/components/` reusable UI components (TaskCard, TaskTable, StatusUpdate, etc.).
- `src/lib/` MCP client and shared helpers.
- `src/hooks/` custom hooks.
- `src/stores/` Zustand stores.
- `src/types/` shared TypeScript models.
- `src/styles/` global Tailwind styles.

## Environment

Create `.env` (or copy `.env.example`):

```
VITE_MCP_BASE_URL=http://localhost:8000
VITE_OAUTH_ENABLED=false
VITE_OAUTH_CLIENT_ID=
```

## Development

Install deps:
```bash
cd ui
npm install
```

Run Vite dev server:
```bash
npm run dev
```

Run lint/typecheck:
```bash
npm run lint
npm run type-check
```

Build:
```bash
npm run build
```

## Storybook

Run Storybook:
```bash
npm run storybook
```

Build static Storybook:
```bash
npm run build-storybook
```

## Notes
- If MCP OAuth is enabled on the server, ensure `VITE_OAUTH_ENABLED=true` and supply a client ID.
- The UI expects MCP endpoints: `/manifest.json`, `/mcp`, and `/health`.
