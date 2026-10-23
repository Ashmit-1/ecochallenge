// Service worker — caches the app shell + static assets only, NEVER /api/* (contract §8).
// Data is always-online per the PWA rules; offline is handled by the React OfflineGuard
// (branded screen + retry) once the shell boots from the cache.
const CACHE_NAME = "ecochallenge-shell-v1";
const SHELL_ASSETS = ["/", "/index.html", "/manifest.json", "/favicon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never intercept API calls: responses are per-user and must not leak or go stale.
  if (url.pathname.startsWith("/api/")) return;
  // Only plain same-origin GETs (no POSTs, no cross-origin CDNs).
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;

  // Navigations: network first so updates arrive; cached shell when offline.
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put("/index.html", copy));
          }
          return response;
        })
        .catch(() =>
          caches.match("/index.html").then((cached) => cached || Response.error()),
        ),
    );
    return;
  }

  // Static assets (hashed JS/CSS/fonts/images): cache first, refresh in background so
  // a cold offline start can still boot the shell the app expects.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      });
    }),
  );
});