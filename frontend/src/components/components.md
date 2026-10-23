# components/

Shared UI primitives and layout wrappers.

| File | Purpose |
|---|---|
| [ui.tsx](ui.tsx) | Button, Card, Chip, IconChip, Skeleton, shaped skeleton loaders (challenge/leaderboard/profile), EmptyState + BotanicalSprout illustration, Input |
| [Layout.tsx](Layout.tsx) | Layout (desktop top nav + mobile bottom tabs), AuthLayout |
| [ProtectedRoute.tsx](ProtectedRoute.tsx) | Auth guards: ProtectedRoute (requires session), PublicOnlyRoute (redirects if logged in) |
