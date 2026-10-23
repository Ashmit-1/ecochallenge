# src/

| Entry | Purpose |
|---|---|
| [main.tsx](main.tsx) | App entry: QueryClient, BrowserRouter, font imports |
| [App.tsx](App.tsx) | Route tree with lazy-loaded pages, Suspense, auth guards |
| [routes/routes.md](routes/routes.md) | Page components: Login, Register, Challenges, Detail, Profile, Leaderboard |
| [components/components.md](components/components.md) | UI primitives, Layout, auth guards, AuthEvents |
| [features/features.md](features/features.md) | Domain components (reserved for future extraction) |
| [lib/lib.md](lib/lib.md) | **Open first:** api.ts (fetch wrapper), queries.ts (query keys/hooks) + their tests |
| [styles/styles.md](styles/styles.md) | Tailwind v4 entry + Fresh Botanical design tokens |
| [types/types.md](types/types.md) | Contract types from frontend-backend-contract.md §3 |
| [test/test.md](test/test.md) | Vitest setup (jest-dom matchers) |
