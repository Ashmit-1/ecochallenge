# src/lib/

| File | Purpose |
|---|---|
| [api.ts](api.ts) | The single fetch wrapper: cookies, CSRF header on writes, 401 → unauthorized handler (never `window.location`), 403-CSRF retry-once, `ApiError` (+ `Retry-After`) |
| [queries.ts](queries.ts) | TanStack Query key factory, typed `queryOptions` for every contract endpoint, mutations (submit, login, register, logout, rename) with contract §7/§8 cache rules |
| [format.ts](format.ts) | `formatCooldown` (server deadline → words, never negative) + `useNow` ticking hook |
| [api.test.ts](api.test.ts) | Credentials, CSRF (incl. `=`-safety), Content-Type/FormData (login regression), 204, error parsing, 403 retry, 401 handler, Retry-After |
| [queries.test.tsx](queries.test.tsx) | Submission flow, header points sync, logout clears caches |
| [queries.challenges.test.tsx](queries.challenges.test.tsx) | Query-key structure + URL/param factory tests |
| [queries.cache.test.tsx](queries.cache.test.tsx) | Post-submit invalidation scope + no token persistence |
| [format.test.ts](format.test.ts) | Countdown formatting edge cases |

Open next: [contract §2](../frontend-backend-contract.md).