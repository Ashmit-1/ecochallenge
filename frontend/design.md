# Frontend design

The owner's frontend choices, translated into something buildable. Read this with
[frontend-backend-contract.md](frontend-backend-contract.md); the contract owns behaviour, this file
owns look, feel, and interaction.

**Direction: Fresh botanical.** Airy whites, leaf greens, soft rounded cards, friendly iconography.
Genuinely human — not a template with a green filter.

---

## 1. Intent

EcoChallenge is about *small actions made visible*. The UI should feel like a well-kept campus field
guide: calm, tactile, optimistic. It should celebrate progress without turning into a game show.

Three feelings to aim for:

1. **"I can do this today."** Challenges look achievable, not like assignments.
2. **"My effort counted."** Points and impact are shown plainly, with honest caveats.
3. **"This app respects me."** No nagging, no fake urgency, no dark patterns.

## 2. Principles

1. **The action is the hero.** The challenge, its photo requirement, and its points dominate the
   screen. Chrome (nav, cards, dividers) stays quiet.
2. **Honest surfaces.** AI verdicts are "checked", never "proven". CO₂ is "estimated", with the
   assumption available on tap.
3. **Warmth over polish.** A hand-drawn leaf, an editorial numeral, and a slightly uneven rhythm
   beat sterile symmetry.
4. **Mobile is the default.** Design at 360 px first; one-handed reach for primary actions.
5. **Motion with meaning.** Only animate to explain a change of state.

## 3. Visual identity

### Colour

| Token | Hex | Use |
|---|---|---|
| `paper` | `#F7F5EE` | Page background (warm off-white, never pure grey) |
| `surface` | `#FFFFFF` | Cards, sheets, inputs |
| `ink` | `#16261E` | Primary text (near-black green) |
| `ink-soft` | `#4A5B51` | Secondary text |
| `moss` | `#2F6B4F` | Primary actions, active nav, links |
| `leaf` | `#6FA98A` | Decorative fills, illustration |
| `mint` | `#DCEBE2` | Icon chips, selected rows, soft highlights |
| `sun` | `#E9B44C` | Points and streaks — **background/chip only**, never body text on white |
| `clay` | `#C4704F` | Rejections, warnings, "needs attention" |
| `danger` | `#A63D2F` | Errors, destructive actions |
| `line` | `#E2E0D6` | 1 px borders and dividers |

Rules: one accent per screen. `moss` for action, `sun` for score, `clay`/`danger` only for
problems. Never colour as the only signal — always pair with an icon and words.

### Typography

| Role | Face | Notes |
|---|---|---|
| Display | **Fraunces** (variable, 600–700, optical size) | Page titles, points, badge names, big impact numbers. Soft serifs give the human edge. |
| UI / body | **Figtree** (variable, 400–600) | Everything else. Friendly, geometric, highly legible. |
| Numerals | Figtree **tabular** | Points, ranks, countdowns so columns do not jump. |

Self-host both via `@fontsource-variable/*` so the PWA works offline. No Google Fonts CDN.

Scale (px / line-height): 12/16, 14/20, 16/26, 18/28, 22/30, 28/34, 36/42, 48/52. Body copy max
width ~68 ch. Headings tight (`1.1`), body relaxed (`1.55`).

### Shape, space, depth

- Radii: controls **14 px**, cards **22 px**, sheets **28 px**, chips/pills full. Deliberately not
  one radius everywhere — that is the template tell.
- Spacing on a 4 px grid. Page gutters 20 px mobile, 32 px tablet, 48 px desktop; max content width
  1120 px.
- Depth: 1 px `line` borders + a soft shadow
  `0 1px 2px rgb(22 38 30 / .06), 0 12px 32px -16px rgb(22 38 30 / .18)`.
  No glassmorphism, no heavy drop shadows.
- Optional: a 3–4% paper-grain SVG overlay on the page background. Subtle enough to feel printed.

### Icons and illustration

- `lucide-react`, 1.75 px stroke, sizes 18/20/24. Category icons sit in a 40 px `mint` circle.
- Never use emoji as UI icons.
- Hand-drawn botanical SVG accents (leaf, sprout, seed, sun) at 1.5 px stroke, rounded caps, used
  sparingly: empty states, auth page, celebration card, section dividers.
- No stock photography in the product chrome. The only photos are the student's own evidence.
- PWA icon: a simple sprout mark on `paper`, 192/512 plus a maskable variant with safe padding.

## 4. Layout and navigation

- **Mobile:** bottom tab bar with three destinations — **Challenges**, **Leaderboard**, **Profile**.
  The submission flow is contextual from a challenge, presented as a full-height sheet.
- **Desktop:** top navigation with wordmark left, the same three tabs, and the student's points chip
  right. Content in a centred 1120 px column; no dense sidebar, no dashboard grid.
- **Auth:** full-screen, wordmark + one short line of copy, form card. Desktop may put a botanical
  illustration opposite; mobile does not.

### Screen intent

| Screen | What it must make obvious |
|---|---|
| Dashboard | One clear next action, your points, and a few challenges with points + cooldown state |
| Challenge | Exactly what to do, what the photo must show, what it earns, and one submit button |
| Submit | The chosen photo, the rules, and an honest "this will be checked" note |
| Result | Approved/rejected, what that means for points, why, and the next action |
| Profile | Points, rank, estimated impact with its caveat, badges, history |
| Leaderboard | Where you stand, without shaming anyone |

Challenge card anatomy: category icon chip · title · one-line tagline · points chip (`sun`) ·
CO₂ chip · cooldown state (available / "again in 6 h") · whole card is the link.

The leaderboard is an editorial list, not a podium. Large tabular rank numerals, name, points,
your row tinted `mint` and labelled "You". Ties show the same rank — do not "fix" them.

## 5. States are part of the design

- **Loading:** skeletons shaped like the real cards. No full-page spinners.
- **Empty:** botanical line illustration + one sentence + one action ("Browse challenges").
- **Verifying:** a calm progress state with honest copy — "Checking your photo. This usually takes
  2–6 seconds." Keep the page stable; disable the submit button.
- **Approved:** points count in, badge card lifts in if `new_badges` is non-empty. Use the returned
  profile — never optimistically add points.
- **Rejected:** `clay` accent, the server's reason verbatim, and a "Try again with a new photo"
  action. Never accuse, never red-alarm.
- **Cooldown:** `sun`-tinted chip with a countdown from `cooldown_ends_at`; the submit button is
  disabled with the reason visible.
- **Offline:** branded screen, "You're offline. Your progress is safe — come back when you're
  connected," and a retry button.
- **Error:** plain language, a retry, and a support hint. Never show stack traces or raw provider
  text.

## 6. Motion

- 160–220 ms, `cubic-bezier(.2,.8,.2,1)`. Page transitions: 8 px rise + fade.
- Card hover on desktop: 2 px lift, border darkens. No tilt, no glow.
- Points: count up once on the result screen (600 ms), never on every render.
- Badge unlock: 0.96 → 1 scale with the card's shadow growing; no confetti.
- Respect `prefers-reduced-motion`: keep opacity fades, drop transforms and count-ups.

## 7. Accessibility and copy

- WCAG 2.2 AA: body text ≥ 4.5:1, large text ≥ 3:1, visible 2 px `moss` focus ring with 2 px
  offset, minimum 44×44 px touch targets, labelled inputs, `aria-live="polite"` for the verdict.
- Status never relies on colour: icon + text for approved, rejected, cooldown, offline.
- Copy: second person, plain verbs, no exclamation spam.
  "You cycled to campus." beats "Congratulations!!! You're a hero!"
- Always visible somewhere honest: AI checks can be wrong; CO₂ figures are estimates
  (pull the exact strings from `GET /meta`).

## 8. Anti-patterns — do not ship these

Purple/blue gradients · glassmorphism · emoji icons · three identical feature cards · one radius
for everything · stock "diverse team" photography · fake AI sparkle motifs · confetti storms ·
fake urgency ("Hurry!") · lorem ipsum · dashboard-dense screens · dark patterns in the cooldown
UI · showing raw confidence scores to students.

## 9. Tokens to start from

```css
:root {
  --paper: #f7f5ee;
  --surface: #ffffff;
  --ink: #16261e;
  --ink-soft: #4a5b51;
  --moss: #2f6b4f;
  --leaf: #6fa98a;
  --mint: #dcebe2;
  --sun: #e9b44c;
  --clay: #c4704f;
  --danger: #a63d2f;
  --line: #e2e0d6;
  --radius-control: 14px;
  --radius-card: 22px;
  --radius-sheet: 28px;
  --shadow-card: 0 1px 2px rgb(22 38 30 / .06), 0 12px 32px -16px rgb(22 38 30 / .18);
}
```

Expose these as Tailwind theme tokens (`bg-paper`, `text-ink`, `border-line`, `bg-mint`,
`text-moss`, `rounded-card`, `shadow-card`) rather than sprinkling hex values through components.

## 10. Scope guard

Light mode only for v1. No dark theme, no theme switcher, no component library that imposes its own
look (build small primitives: Button, Card, Chip, Progress, Sheet, EmptyState). The design should be
recognisable from a screenshot at 360 px wide.
