/// <reference types="node" />
/**
 * Regression tests for the font swap: Fraunces + Figtree were replaced by
 * the self-hosted variable families Newsreader (display) + Manrope (body).
 *
 * Guards the two places the swap can silently regress:
 *   - `src/main.tsx` must import the two new @fontsource-variable packages and nothing old.
 *   - `package.json` must list the two new packages as dependencies and drop the old ones
 *     (stale font packages are dead weight under the repo's "no unused dependencies" rule).
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const STYLES_DIR = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_DIR = path.resolve(STYLES_DIR, "..", ".."); // …/frontend
const mainTsx = readFileSync(path.join(FRONTEND_DIR, "src", "main.tsx"), "utf8");
const pkg = JSON.parse(
  readFileSync(path.join(FRONTEND_DIR, "package.json"), "utf8"),
) as { dependencies?: Record<string, string> };

const depNames = Object.keys(pkg.dependencies ?? {});
const NEW_FONTS = [
  "@fontsource-variable/newsreader",
  "@fontsource-variable/manrope",
];
const OLD_FONTS = ["@fontsource-variable/fraunces", "@fontsource-variable/figtree"];

describe("src/main.tsx font imports", () => {
  it("imports both new fontsource-variable packages", () => {
    expect(mainTsx).toContain('import "@fontsource-variable/newsreader";');
    expect(mainTsx).toContain('import "@fontsource-variable/manrope";');
  });

  it("no longer imports fraunces or figtree", () => {
    expect(mainTsx.toLowerCase()).not.toContain("fraunces");
    expect(mainTsx.toLowerCase()).not.toContain("figtree");
  });
});

describe("package.json font dependencies", () => {
  it("declares both new font packages as dependencies", () => {
    for (const name of NEW_FONTS) {
      expect(depNames, `${name} missing from dependencies`).toContain(name);
    }
  });

  it("drops the old fraunces/figtree packages entirely", () => {
    const stale = OLD_FONTS.filter((name) => depNames.includes(name));
    expect(
      stale,
      `stale font packages still in dependencies: ${stale.join(", ")}`,
    ).toEqual([]);
  });
});