# public/

Static assets copied to the build root.

| Entry | Purpose |
|---|---|
| [manifest.json](manifest.json) | PWA manifest: standalone display, moss theme color, 192/512/maskable icons |
| [sw.js](sw.js) | Service worker: caches the app shell only — **never `/api/*`** (contract §8) |
| [favicon.svg](favicon.svg) | Sprout mark favicons |
| [icons/icons.md](icons/icons.md) | PWA icon PNGs |
