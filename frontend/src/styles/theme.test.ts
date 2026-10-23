/// <reference types="node" />
/**
 * Regression tests for the Fresh Botanical theme surface of `src/styles/index.css`.
 *
 * Guards added with the font swap + eco-doodle wallpaper change:
 *   1. fonts: `--font-display` → Newsreader Variable, `--font-body` → Manrope Variable,
 *      and no stale Fraunces/Figtree references left behind in the stylesheet.
 *   2. wallpaper: well-formed `--field-doodle` data-URI token, `@utility bg-field`,
 *      body sizing, plus structure checks on the decoded SVG tile.
 *   3. sync: `scripts/gen-doodle.py` must emit exactly the declaration embedded in
 *      index.css — the generator docstring is the source of truth for the artwork,
 *      so this doubles as the asset-in-sync / motif-containment guard.
 *   4. usage: no `.tsx` still asks for `bg-paper` on a full-page surface; every
 *      `min-h-screen` page wrapper renders `bg-field` (paper + wallpaper).
 */
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import cssRaw from "./index.css?raw";

const STYLES_DIR = path.dirname(fileURLToPath(import.meta.url));
const SRC_DIR = path.resolve(STYLES_DIR, ".."); // …/frontend/src
const FRONTEND_DIR = path.resolve(STYLES_DIR, "..", ".."); // …/frontend
const GEN_SCRIPT = "scripts/gen-doodle.py";

/**
 * The stylesheet under test.
 *
 * `?raw` is the idiomatic loader, but this project keeps Vitest's default
 * `test.css: false`, under which Vite short-circuits CSS module requests —
 * including `?raw` (`?raw` on a non-CSS file works) — to an empty string.
 * When the raw import yields nothing, read the very same file from disk so
 * the assertions always run against the real source text.
 */
const css =
  cssRaw.length > 0 ? cssRaw : readFileSync(path.join(STYLES_DIR, "index.css"), "utf8");

/** The whole `--field-doodle: …;` declaration as trailing CSS text (no `;` occurs inside the encoded URI). */
const doodleDeclaration = css.match(/--field-doodle:[^;]*;/)?.[0] ?? null;

/** The percent-encoded data URI embedded in the stylesheet (no raw `"` inside — quotes are %22). */
const rawDataUri = css.match(/url\("(data:image\/svg\+xml,[^"]+)"\)/)?.[1] ?? null;

const decodedSvg = rawDataUri
  ? decodeURIComponent(rawDataUri).replace(/^data:image\/svg\+xml,/, "")
  : "";

describe("font tokens in index.css", () => {
  it("publishes --font-display as the exact Newsreader Variable family", () => {
    expect(css.length).toBeGreaterThan(0); // sanity: stylesheet actually loaded
    expect(css).toContain('--font-display: "Newsreader Variable", Georgia, serif;');
  });

  it("publishes --font-body as the exact Manrope Variable family", () => {
    expect(css).toContain(
      '--font-body: "Manrope Variable", ui-sans-serif, system-ui, sans-serif;',
    );
  });

  it("contains no stale Fraunces or Figtree references", () => {
    const lower = css.toLowerCase();
    expect(lower).not.toContain("fraunces");
    expect(lower).not.toContain("figtree");
    expect(lower).toContain("newsreader");
    expect(lower).toContain("manrope");
  });
});

describe("eco-doodle wallpaper token", () => {
  it("declares --field-doodle as a single url(data:image/svg+xml,…) entry", () => {
    expect(doodleDeclaration).not.toBeNull();
    expect(doodleDeclaration).toContain("data:image/svg+xml");
    // Guards the well-formedness of the declaration itself: exactly one property
    // name followed directly by url("data:image/svg+xml, … ".
    expect(doodleDeclaration).toMatch(/^--field-doodle:\s*url\("data:image\/svg\+xml,/);
  });

  it("tiles the artwork at a 300px background-size", () => {
    expect(css).toMatch(/background-size:\s*300px\s+300px/);
  });

  it("wires the wallpaper into body", () => {
    const bodyBlock = css.match(/\nbody\s*\{[^}]*\}/)?.[0] ?? "";
    expect(bodyBlock).toContain("background-image: var(--field-doodle);");
    expect(bodyBlock).toContain("background-repeat: repeat;");
    expect(bodyBlock).toMatch(/background-size:\s*300px\s+300px/);
  });

  it("defines the Tailwind v4 @utility bg-field on top of the wallpaper", () => {
    // No nested braces inside the block, so [^}]* is bounded to this utility.
    expect(css).toMatch(
      /@utility\s+bg-field\s*\{[^}]*background-color:\s*var\(--color-paper\)[^}]*background-image:\s*var\(--field-doodle\)[^}]*background-size:\s*300px\s+300px[^}]*\}/,
    );
  });
});

describe("doodle data URI decodes to the expected tile", () => {
  it("decodes to a 300x300 inline SVG with the moss stroke at 0.14 opacity", () => {
    expect(rawDataUri).not.toBeNull();
    expect(decodedSvg.startsWith("<svg")).toBe(true);
    expect(decodedSvg).toContain('viewBox="0 0 300 300"');
    expect(decodedSvg).toContain('stroke-opacity="0.14"');
    expect(decodedSvg).toContain('stroke="#2F6B4F"');
    expect(decodedSvg.endsWith("</svg>")).toBe(true);
  });

  it("keeps every motif group's translate inside the 300x300 tile window", () => {
    // The artwork is drawn around the tile centre: a wrapper group carries
    // translate(150,150) and each motif is placed at a local offset from it.
    const centre = 'transform="translate(150,150)"';
    expect(decodedSvg).toContain(centre);

    const motifSection = decodedSvg.slice(decodedSvg.indexOf(centre) + centre.length);
    const offsets = [...motifSection.matchAll(/translate\((-?[\d.]+),(-?[\d.]+)\)/g)]
      .map(([, x, y]) => ({ x: Number(x), y: Number(y) }))
      .filter(({ x, y }) => x !== 150 || y !== 150);

    // Coarse geometric guard: motif origins must sit within 135px of the centre,
    // i.e. at least 15px clear of every tile edge. The generator's artwork extents
    // (≤36px past an origin, e.g. the big leaf at (90,-80), the sun at (-120,-8))
    // then stay inside 0..300, so `background-repeat` tiles seamlessly.
    expect(offsets.length).toBeGreaterThanOrEqual(10);
    for (const { x, y } of offsets) {
      expect(Math.abs(x)).toBeLessThanOrEqual(135);
      expect(Math.abs(y)).toBeLessThanOrEqual(135);
    }
  });
});

describe("asset-in-sync: scripts/gen-doodle.py ↔ index.css", () => {
  it("generator output matches the --field-doodle declaration embedded in index.css exactly", () => {
    expect(existsSync(path.join(FRONTEND_DIR, GEN_SCRIPT))).toBe(true);

    const gen = spawnSync("python3", [GEN_SCRIPT], {
      cwd: FRONTEND_DIR,
      encoding: "utf8",
    });
    expect(gen.status, `generator failed:\n${gen.stderr}`).toBe(0);

    const genLine = gen.stdout
      .split("\n")
      .find((line) => line.startsWith("--field-doodle:"))
      ?.trim();
    expect(genLine, "generator printed no --field-doodle: line").toBeTruthy();

    const cssLine = css
      .split("\n")
      .find((line) => line.includes("--field-doodle:"))
      ?.trim();
    expect(cssLine, "index.css has no --field-doodle: line").toBeTruthy();

    // Exact string equality: if the artwork, its encoding, or the embedded CSS drifts
    // apart from the generator, the wallpaper silently changes (or breaks outright).
    expect(cssLine).toBe(genLine);
  });
});

describe("tsx full-page surfaces", () => {
  const tsxFiles = readdirSync(SRC_DIR, { recursive: true, encoding: "utf8" })
    .filter((rel) => rel.endsWith(".tsx"))
    .map((rel) => path.join(SRC_DIR, rel))
    .sort();

  const sources = tsxFiles.map((abs) => ({
    abs,
    text: readFileSync(abs, "utf8"),
  }));

  it("found the .tsx files to scan", () => {
    expect(tsxFiles.length).toBeGreaterThan(0);
  });

  it("no .tsx uses bg-paper any more (it would paint over the wallpaper)", () => {
    const offenders = sources
      .filter(({ text }) => text.includes("bg-paper"))
      .map(({ abs }) => path.relative(FRONTEND_DIR, abs));
    expect(offenders).toEqual([]);
  });

  it("every min-h-screen full-page surface renders with bg-field", () => {
    const offenders: string[] = [];
    let surfaces = 0;
    for (const { abs, text } of sources) {
      for (const line of text.split("\n")) {
        if (!line.includes("min-h-screen")) continue;
        surfaces += 1;
        if (!line.includes("bg-field")) {
          offenders.push(`${path.relative(FRONTEND_DIR, abs)}: ${line.trim()}`);
        }
      }
    }
    expect(offenders).toEqual([]);
    expect(surfaces).toBeGreaterThanOrEqual(6);
  });
});