# UI Workspace

## Storybook (component preview)

Storybook lets you preview UI components in isolation with Tailwind + shadcn styles.

### Setup

```bash
cd ui
npm install
```

### Run Storybook

```bash
npm run storybook
```

Storybook runs at `http://localhost:6006`.

### Build Storybook (static)

```bash
npm run build-storybook
```

### Notes

- Tailwind styles are loaded from `src/styles/globals.css` via `.storybook/preview.ts`.
- Storybook v10 no longer ships the legacy addon packages (`addon-essentials`, `addon-interactions`, `addon-links`, `blocks`, `test`). If you see migration warnings, remove those deps and keep `storybook` + `@storybook/react-vite` only.
- If you see permission errors writing into `ui/node_modules`, remove it and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

## Vite app (full UI)

```bash
cd ui
npm run dev
```

Vite runs at `http://localhost:5173` by default.
