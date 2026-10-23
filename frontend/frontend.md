# frontend/

The React single-page PWA. **Milestones 1–4 + bugfix complete** — scaffold, typed API client,
TanStack Query layer, PWA shell, all six screens, auth flow, design polish + accessibility,
contract tests, and a live end-to-end check through the dev proxy.
See [src/src.md](src/src.md) for the source map.

| Entry | Purpose |
|---|---|
| [frontend-backend-contract.md](frontend-backend-contract.md) | **The only source of truth about the backend.** Auth, endpoints, types, errors, PWA rules |
| [design.md](design.md) | Visual direction, palette, type, layout, states, motion, accessibility, anti-patterns |
| [src/src.md](src/src.md) | Source tree navigation |
| README.md | Run/verify commands for the frontend |

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

## Structure (as built)

```
frontend/
├── src/
│   ├── main.tsx            app entry: QueryClient, BrowserRouter, fonts, service-worker registration
│   ├── App.tsx             route tree; lazy pages; <AuthEvents/> wires the 401→/login handler
│   ├── routes/             one file per page: Login, Register, Challenges, ChallengeDetail,
│   │                       Profile, Leaderboard (+ routes.md, tests live in components/lib)
│   ├── components/         ui.tsx primitives, Layout (top/bottom nav), ProtectedRoute/PublicOnlyRoute
│   │                       guards, AuthEvents (+ components.md)
│   ├── features/           reserved for extraction from routes (empty; features.md explains)
│   ├── lib/                api.ts (the single fetch wrapper; never navigates), queries.ts
│   │                       (key factory + typed hooks/mutations) + their tests (+ lib.md)
│   ├── styles/             index.css: Tailwind v4 @import, Fresh Botanical @theme tokens,
│   │                       motion + focus classes (there is no tailwind.config file)
│   ├── types/              contract types from contract §3 (+ types.md)
│   └── test/setup.ts       jest-dom matchers for Vitest (+ test.md)
├── public/                 manifest.json, sw.js (app shell only, never /api/*), favicon.svg,
│   │                       icons/ (192, 512, maskable) (+ public.md, icons/icons.md)
├── scripts/generate-icons.ts  regenerates the PWA icon PNGs from the sprout SVG (+ scripts.md)
├── index.html
├── vite.config.ts          dev proxy /api → http://127.0.0.1:8000; vitest config (`test` key)
├── tsconfig*.json          NOTE: root tsconfig is references-only — typecheck with `tsc -b`, not bare `tsc --noEmit` (which checks nothing)
├── package.json            scripts: dev, build (tsc -b && vite build), preview, lint, test
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

## Verification gate

Run from `frontend/` (Bun needs `BUN_TMPDIR=/tmp/bun-tmp BUN_INSTALL=/tmp/bun-install` if its
cache dir is read-only):

```bash
bunx tsc -b          # the REAL type gate — bare `tsc --noEmit` checks nothing (references-only root tsconfig)
bunx vitest run      # API client, auth guards, submission flow, regression tests
bunx vite build      # production bundle
```

## Running

The backend must be running (`cd backend && uv run fastapi dev`), seeded
(`uv run alembic upgrade head && uv run seed`), and either using a real `GEMINI_API_KEY` or
`VISION_PROVIDER=mock`. Then `bun run dev` starts the frontend on http://127.0.0.1:5173 with
`/api` proxied to the backend. See [../PROJECT_STATE.md](../PROJECT_STATE.md).
