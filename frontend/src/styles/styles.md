# src/styles/

| File | Purpose |
|---|---|
| [index.css](index.css) | Tailwind v4 entry: `@import "tailwindcss"`, Fresh Botanical `@theme` tokens (paper/moss/leaf/sun/clay…), Newsreader/Manrope font pair, `--field-doodle` wallpaper + `bg-field` utility (use instead of `bg-paper` for full-screen surfaces; regenerate with `python3 ../scripts/gen-doodle.py`, verify with `bun run ../scripts/check-doodle.ts`), paper-grain overlay, motion classes (rise-in, card-hover, badge-pop, points-reveal), `prefers-reduced-motion`, global focus ring |

There is no tailwind.config file — v4 is CSS-first. Design spec: [design.md](../../design.md).
