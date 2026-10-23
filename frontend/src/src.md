# src/

| Entry | Purpose |
|---|---|
| [main.tsx](main.tsx) | App entry: QueryClient, BrowserRouter, font imports |
| [App.tsx](App.tsx) | Route tree with lazy-loaded pages, Suspense, auth guards |
| [routes/routes.md](routes/routes.md) | Page components: Login, Register, Challenges, Detail, Profile, Leaderboard |
| [components/components.md](components/components.md) | UI primitives, Layout, ProtectedRoute |
| [features/](features/) | Domain components (reserved for future extraction) |
| [lib/api.ts](lib/api.ts) | Single fetch wrapper with CSRF + cookie auth |
| [lib/queries.ts](lib/queries.ts) | TanStack Query keys, options, mutations |
| [styles/index.css](styles/index.css) | Tailwind entry + Fresh Botanical design tokens |
| [types/index.ts](types/index.ts) | Contract types from frontend-backend-contract.md §3 |
| [test/setup.ts](test/setup.ts) | Vitest setup (jest-dom matchers) |
