# src/

| Entry | Purpose |
|---|---|
| [main.tsx](main.tsx) | App entry: QueryClient, BrowserRouter, font imports |
| [App.tsx](App.tsx) | Route tree (placeholder routes for now) |
| [routes/](routes/) | One file per page (not yet built) |
| [components/](components/) | Shared UI primitives (not yet built) |
| [features/](features/) | Domain components (not yet built) |
| [lib/api.ts](lib/api.ts) | Single fetch wrapper with CSRF + cookie auth |
| [lib/queries.ts](lib/queries.ts) | TanStack Query keys, options, mutations |
| [styles/index.css](styles/index.css) | Tailwind entry + Fresh Botanical design tokens |
| [types/index.ts](types/index.ts) | Contract types from frontend-backend-contract.md §3 |
| [test/setup.ts](test/setup.ts) | Vitest setup (jest-dom matchers) |
