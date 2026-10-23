import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSubmitEvidence, useLogout } from "./queries";
import type { Badge, Profile, Submission } from "../types";

const oldProfile: Profile = {
  display_name: "Student",
  email: "s@campus.edu",
  points_total: 0,
  submissions_total: 0,
  submissions_approved: 0,
  submissions_rejected: 0,
  challenges_completed: 0,
  co2_saved_grams: 0,
  rank: 3,
  total_participants: 5,
  badges: [],
  member_since: "2026-01-01T00:00:00Z",
};

const updatedProfile: Profile = {
  ...oldProfile,
  points_total: 50,
  submissions_total: 1,
  submissions_approved: 1,
  challenges_completed: 1,
  co2_saved_grams: 1000,
  rank: 1,
};

const badge: Badge = {
  key: "first_steps",
  name: "First Steps",
  description: "Complete your first challenge",
  icon: "sprout",
  earned: true,
  current: 1,
  target: 1,
};

const submission: Submission = {
  id: 1,
  challenge: { id: 1, slug: "bike-to-campus", title: "Bike to Campus", points: 50, icon: "bike" },
  status: "approved",
  points_awarded: 50,
  co2_saved_grams: 1000,
  verification: { approved: true, confidence: 0.95, reason: "Photo matches", model: "test" },
  image_url: "/api/v1/submissions/1/image",
  created_at: "2026-10-23T10:00:00Z",
  verified_at: "2026-10-23T10:00:05Z",
};

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}

describe("useSubmitEvidence (submission flow)", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "ecochallenge_csrf=csrf-token-1",
    });
  });

  it("posts multipart FormData to the challenge submissions endpoint", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({ submission, profile: updatedProfile, new_badges: [badge] }),
    });

    const { client, wrapper } = createWrapper();
    client.setQueryData(["profile"], oldProfile);
    const file = new File(["photo-bytes"], "bike-campus.jpg", { type: "image/jpeg" });

    const { result } = renderHook(() => useSubmitEvidence("bike-to-campus"), { wrapper });
    await result.current.mutateAsync(file);

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/v1/challenges/bike-to-campus/submissions");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("image")).toBe(file);
    // CSRF header present (POST), Content-Type left to the browser for multipart
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("csrf-token-1");
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
  });

  it("applies the returned profile instead of adding points optimistically (contract §7)", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({ submission, profile: updatedProfile, new_badges: [badge] }),
    });

    const { client, wrapper } = createWrapper();
    client.setQueryData(["profile"], oldProfile);
    const file = new File(["photo-bytes"], "bike-campus.jpg", { type: "image/jpeg" });

    const { result } = renderHook(() => useSubmitEvidence("bike-to-campus"), { wrapper });
    await result.current.mutateAsync(file);

    expect(client.getQueryData(["profile"])).toEqual(updatedProfile);
  });
});

describe("useLogout (contract §8: clear caches)", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
  });

  it("clears all TanStack Query caches on successful logout", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, status: 204 });

    const { client, wrapper } = createWrapper();
    client.setQueryData(["profile"], oldProfile);
    const [beforeProfile, beforeTotal] = [
      client.getQueryData(["profile"]),
      client.getQueryCache().getAll().length,
    ];
    expect(beforeProfile).toEqual(oldProfile);
    expect(beforeTotal).toBeGreaterThan(0);

    const { result } = renderHook(() => useLogout(), { wrapper });
    await result.current.mutateAsync();

    expect(client.getQueryCache().getAll()).toHaveLength(0);
    const [url, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/v1/auth/logout");
    expect(init.method).toBe("POST");
  });
});
describe("useSubmitEvidence header sync (audit finding #4)", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "ecochallenge_csrf=csrf-token-1",
    });
  });

  it("mirrors the returned profile points into the `me` cache so the header chip updates", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({ submission, profile: updatedProfile, new_badges: [badge] }),
    });

    const { client, wrapper } = createWrapper();
    const meBefore = {
      id: 7,
      email: "s@campus.edu",
      display_name: "Student",
      points_total: 0,
      created_at: "2026-01-01T00:00:00Z",
    };
    client.setQueryData(["auth", "me"], meBefore);
    client.setQueryData(["profile"], oldProfile);

    const file = new File(["photo-bytes"], "bike-campus.jpg", { type: "image/jpeg" });
    const { result } = renderHook(() => useSubmitEvidence("bike-to-campus"), { wrapper });
    await result.current.mutateAsync(file);

    const me = client.getQueryData(["auth", "me"]) as typeof meBefore;
    expect(me.points_total).toBe(updatedProfile.points_total); // 50 from server response
    expect(me.id).toBe(7); // other fields untouched
    expect(client.getQueryData(["profile"])).toEqual(updatedProfile);
  });

  it("leaves `me` untouched when it is not cached (logged-out edge)", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({ submission, profile: updatedProfile, new_badges: [] }),
    });

    const { client, wrapper } = createWrapper();
    const file = new File(["photo-bytes"], "bike-campus.jpg", { type: "image/jpeg" });
    const { result } = renderHook(() => useSubmitEvidence("bike-to-campus"), { wrapper });
    await result.current.mutateAsync(file);

    expect(client.getQueryData(["auth", "me"])).toBeUndefined();
  });
});
