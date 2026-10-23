import { describe, it, expect } from "vitest";
import { formatCooldown } from "./format";

const NOW = Date.parse("2026-10-23T12:00:00Z");

describe("formatCooldown", () => {
  it("returns null when there is no deadline", () => {
    expect(formatCooldown(null, NOW)).toBeNull();
  });

  it("returns null when the deadline is exactly now", () => {
    expect(formatCooldown("2026-10-23T12:00:00Z", NOW)).toBeNull();
  });

  it("returns null for a past deadline — never emits negative countdowns", () => {
    expect(formatCooldown("2026-10-23T11:59:00Z", NOW)).toBeNull();
    expect(formatCooldown("2026-10-22T12:00:00Z", NOW)).toBeNull();
  });

  it("formats hours and minutes", () => {
    expect(formatCooldown("2026-10-23T18:15:00Z", NOW)).toBe("6h 15m");
  });

  it("formats minutes only under an hour", () => {
    expect(formatCooldown("2026-10-23T12:45:00Z", NOW)).toBe("45m");
  });

  it("formats sub-minute deadlines as words", () => {
    expect(formatCooldown("2026-10-23T12:00:30Z", NOW)).toBe("less than a minute");
  });
});