# scripts/

| File | Purpose |
|---|---|
| [generate-icons.ts](generate-icons.ts) | Renders the sprout SVG to public/icons/ (192, 512, maskable) via sharp (`bun run scripts/generate-icons.ts`) |
| [check-doodle.ts](check-doodle.ts) | Reproducible wallpaper verification: CSS embed matches generator exactly (guards doubled/invalid declarations), `body`/`bg-field` consume it, pixel-coverage per 300px tile region (`bun run scripts/check-doodle.ts`) |
| [gen-doodle.py](gen-doodle.py) | Generates the wallpaper tile: prints the `--field-doodle` CSS (paste into src/styles/index.css); `--preview out.svg` renders a 3×2 visual check (`python3 scripts/gen-doodle.py`) |

Run these when the PWA mark or the wallpaper changes; run check-doodle.ts before committing any wallpaper change. See [public/icons/icons.md](../public/icons/icons.md) and design.md §3 Wallpaper.
