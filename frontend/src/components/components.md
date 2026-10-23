# components/

Shared UI primitives and layout wrappers.

| File | Purpose |
|---|---|
| [ui.tsx](ui.tsx) | Button, Card, Chip, IconChip, Skeleton, shaped skeleton loaders (challenge/leaderboard/profile), EmptyState + BotanicalSprout illustration, Input |
| [Layout.tsx](Layout.tsx) | Layout (desktop top nav + mobile bottom tabs), AuthLayout |
| [ProtectedRoute.tsx](ProtectedRoute.tsx) | Auth guards: ProtectedRoute (requires session), PublicOnlyRoute (redirects if logged in) |
| [AuthEvents.tsx](AuthEvents.tsx) | Registers the API client 401 handler; routes to /login via React Router (never hard navigation), with a same-path guard |
| [ProtectedRoute.test.tsx](ProtectedRoute.test.tsx) | Guard tests: authenticated render vs redirect for both routes |
| [OfflineGuard.tsx](OfflineGuard.tsx) | Wraps the app; branded offline screen with retry (contract §8), live online/offline events |
| [OfflineGuard.test.tsx](OfflineGuard.test.tsx) | Offline screen/render/react-to-events tests |
| [AuthEvents.test.tsx](AuthEvents.test.tsx) | 401 routing tests: redirects to /login once, no loop when already on an auth page |
