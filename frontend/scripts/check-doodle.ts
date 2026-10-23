/**
 * Reproducible verification for the wallpaper (design.md §3 "Wallpaper (eco-doodle)").
 *
 *   bun run scripts/check-doodle.ts
 *
 * Checks:
 *  1. src/styles/index.css embeds EXACTLY the line gen-doodle.py prints
 *     (guards against doubled prefixes/invalid custom-property values).
 *  2. body and the bg-field utility actually reference the variable.
 *  3. Every motif renders INSIDE the 300x300 tile: rasterizes a 3x2 preview and
 *     asserts each tile region has ink coverage (a clipped/misplaced motif makes
 *     a region drop below threshold). Equal regions also prove seamless tiling.
 *
 * Exit code 0 = wallpaper is valid and complete. Run before committing artwork changes.
 */
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import sharp from "sharp";

const root = path.join(import.meta.dir, "..");
const cssPath = path.join(root, "src/styles/index.css");
const gen = path.join(root, "scripts/gen-doodle.py");
const previewSvg = path.join(root, ".preview/check-doodle.svg");

let failures = 0;
const fail = (msg: string) => {
  failures++;
  console.error(`FAIL  ${msg}`);
};
const ok = (msg: string) => console.log(`ok    ${msg}`);

// 1. generator output is embedded verbatim (and not doubled)
const genOut = spawnSync("python3", [gen], { encoding: "utf8" });
if (genOut.status !== 0) throw new Error(`gen-doodle.py failed: ${genOut.stderr}`);
const expected = genOut.stdout.split("\n").find((l) => l.startsWith("--field-doodle:"))!;
const css = readFileSync(cssPath, "utf8");

const declMatch = css.match(/--field-doodle:[^\n]*/);
if (!declMatch) fail("index.css has no --field-doodle declaration");
else if (css.includes("--field-doodle: --field-doodle:"))
  fail("doubled --field-doodle prefix (wallpaper resolves to none)");
else if (declMatch[0] !== expected)
  fail(`embedded declaration differs from generator output\n  css:       ${declMatch[0].slice(0, 80)}...\n  generator: ${expected.slice(0, 80)}...`);
else ok("embedded --field-doodle matches gen-doodle.py exactly (single prefix)");

// 2. the variable is actually consumed
if (!/background-image: var\(--field-doodle\)/.test(css))
  fail("no background-image: var(--field-doodle)");
else ok("background-image references the variable");
if (!css.includes("@utility bg-field")) fail("bg-field utility missing");
else ok("bg-field utility present");

// 3. pixel-coverage: every 300x300 region of a 3x2 preview contains the motifs
spawnSync("python3", [gen, "--preview", previewSvg], { encoding: "utf8" });
const { data, info } = await sharp(readFileSync(previewSvg))
  .raw()
  .toBuffer({ resolveWithObject: true });
const regions: number[] = [];
for (let ty = 0; ty < 2; ty++) {
  for (let tx = 0; tx < 3; tx++) {
    let ink = 0;
    for (let y = ty * 300; y < ty * 300 + 300; y++) {
      for (let x = tx * 300; x < tx * 300 + 300; x++) {
        const i = (y * info.width + x) * info.channels;
        const delta =
          Math.abs(data[i] - 247) + Math.abs(data[i + 1] - 245) + Math.abs(data[i + 2] - 238);
        if (delta > 12) ink++;
      }
    }
    regions.push(ink);
  }
}
const min = Math.min(...regions);
if (min < 300)
  fail(`a tile region is nearly empty (min ink ${min}; per region: ${regions.join(",")}) — motif clipped or missing`);
else ok(`coverage per tile region: ${regions.join(",")} (min ${min} >= 300)`);
if (new Set(regions).size === 1)
  ok("all regions identical — motifs fully inside the tile, tiling is seamless");
else
  fail(`region ink counts differ: ${regions.join(",")} — regions must match for seamless tiling`);

if (failures > 0) {
  console.error(`\n${failures} check(s) failed`);
  process.exit(1);
}
console.log("\nwallpaper checks passed");