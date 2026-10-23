// lib/format.ts — pure display helpers shared by challenge screens.
import { useEffect, useState } from "react";

/**
 * Format a server-computed cooldown deadline into "6h 12m" / "45m".
 * Never recalculate cooldown logic from other fields (contract §7) —
 * this only turns `cooldown_ends_at` into words.
 * Returns null when no cooldown remains (so negative values never display).
 */
export function formatCooldown(endsAt: string | null, now: number = Date.now()): string | null {
  if (!endsAt) return null;
  const diffMs = new Date(endsAt).getTime() - now;
  if (diffMs <= 0) return null;
  const hours = Math.floor(diffMs / 3_600_000);
  const minutes = Math.floor((diffMs % 3_600_000) / 60_000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return "less than a minute";
}

/**
 * Re-render on an interval so countdowns keep ticking while the page is open
 * (default 30 s — minutes-resolution countdowns don't need to be tighter).
 */
export function useNow(intervalMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}