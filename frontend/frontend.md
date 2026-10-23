# frontend/

The React single-page PWA. **Milestone 1 complete** — scaffold, typed API client, TanStack Query
layer, PWA shell, and tests are live. See [src/src.md](src/src.md) for the source map.

| Entry | Purpose |
|---|---|
| [frontend-backend-contract.md](frontend-backend-contract.md) | **The only source of truth about the backend.** Auth, endpoints, types, errors, PWA rules |
| [design.md](design.md) | Visual direction, palette, type, layout, states, motion, accessibility, anti-patterns |
| [src/src.md](src/src.md) | Source tree navigation |

## Locked decisions

| Area | Decision |
|---|---|
| Framework | React + Vite + TypeScript |
| Styling | Tailwind CSS, mobile-first, Fresh botanical theme |
| Runtime / package manager | Bun |
| Data + routing | TanStack Query + React Router |
| Auth | httpOnly cookie session + `X-CSRF-Token` (already implemented in the backend) |
| PWA | Installable app shell; **data always online**, no offline cache or queue |
| Icons | `lucide-react` (names come from the API; see the contract's icon mapping) |
| Theme | Fresh botanical — airy whites, leaf greens, soft rounded cards, friendly iconography; genuinely human, not a template. Full spec: [design.md](design.md) |

## Planned structure

```
frontend/
├── src/
│   ├── main.tsx            app entry, QueryClient + Router
│   ├── App.tsx             route tree
│   ├── routes/             one file per page (dashboard, challenge, submit, profile, leaderboard, auth)
│   ├── components/         shared UI: layout, nav, cards, badges, empty/error states
│   ├── features/           domain components (challenges, submissions, profile)
│   ├── lib/                api.ts (the single fetch wrapper), queries.ts, format.ts, cookies.ts
│   ├── styles/             tailwind entry + design tokens
│   └── types/              contract types
├── public/icons/           PWA icons (192, 512, maskable)
├── index.html
├── vite.config.ts          dev proxy /api → http://127.0.0.1:8000
├── tailwind config, tsconfig, package.json
└── frontend.md             this file
```

Every folder gets its own `<folder>.md`. Keep them short; they are a map, not a manual.

## Rules for the frontend agent

- **Read the contract before writing code.** If it is silent, ask; do not infer from backend source.
- All HTTP goes through `src/lib/api.ts` — credentials included, CSRF header on writes.
- Never store the JWT; auth state comes from `GET /auth/me`.
- Never cache `/api/*` in the service worker.
- Do not change the backend without the owner's approval; if a backend change is agreed, update the
  contract in the same commit.
- Mobile and laptop are equally first-class; test both widths.
- Add tests for the API client, auth guard, and submission flow at minimum.

## Before starting

The backend must be running (`cd backend && uv run fastapi dev`), seeded
(`uv run alembic upgrade head && uv run seed`), and either using a real `GEMINI_API_KEY` or
`VISION_PROVIDER=mock`. See [../PROJECT_STATE.md](../PROJECT_STATE.md).
