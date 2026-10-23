import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { queryKeys, useLogin, useSubmitEvidence } from "./queries";
import type { AuthResponse, Profile, Submission, User } from "../types";

// Focused gap tests: (1) dependent-cache invalidation coverage after a
// submission, (2) contract §2 — the SPA must ignore access_token.

const user: User = {
  id: 1,
  email: "student@campus.edu",
  display_name: "Test Student",
  points_total: 50,
  created_at: "2026-01-01T00:00:00Z",
};

const returnedProfile: Profile = {
  display_name: "Test Student",
  email: "student@campus.edu",
  points_total: 100,
  submissions_total: 1,
  submissions_approved: 1,
  submissions_rejected: 0,
  challenges_completed: 1,
  co2_saved_grams: 1000,
  rank: 1,
  total_participants: 5,
  badges: [],
  member_since: "2026-01-01T00:00:00Z",
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

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
}

function createWrapper(client: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

function isInvalidated(client: QueryClient, queryKey: readonly unknown[]): boolean | undefined {
  const query = client.getQueryCache().find({ queryKey });
  return query?.state.isInvalidated;
}

describe("useSubmitEvidence invalidates every dependent cache", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "ecochallenge_csrf=csrf-token-1",
    });
  });

  it("marks challenge detail, challenges list, submissions list, and leaderboard keys stale", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ submission, profile: returnedProfile, new_badges: [] }),
    });

    const client = createClient();
    const dependentKeys: readonly (readonly unknown[])[] = [
      queryKeys.challenges.list(),
      queryKeys.challenges.detail("bike-to-campus"),
      queryKeys.submissions.list({ limit: 10 }),
      queryKeys.leaderboard({ limit: 10 }),
    ];
    const untouchedKeys: readonly (readonly unknown[])[] = [
      queryKeys.meta,
      queryKeys.health,
      queryKeys.me,
    ];
    for (const key of [...dependentKeys, ...untouchedKeys]) {
      client.setQueryData(key, { seeded: true });
    }

    const { result } = renderHook(() => useSubmitEvidence("bike-to-campus"), {
      wrapper: createWrapper(client),
    });
    const file = new File(["photo"], "bike.jpg", { type: "image/jpeg" });
    await result.current.mutateAsync(file);

    for (const key of dependentKeys) {
      expect(
        isInvalidated(client, key),
        `expected ${JSON.stringify(key)} to be invalidated`,
      ).toBe(true);
    }
    for (const key of untouchedKeys) {
      expect(
        isInvalidated(client, key),
        `expected ${JSON.stringify(key)} to be left alone`,
      ).toBe(false);
    }
    // profile is replaced (not just invalidated) with the server's response
    expect(client.getQueryData(queryKeys.profile)).toEqual(returnedProfile);
  });
});

describe("useLogin ignores access_token (contract §2)", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
  });

  it("stores only the user in the query cache and never the token", async () => {
    const authResponse: AuthResponse = {
      access_token: "SECRET.JWT.TOKEN.VALUE",
      token_type: "bearer",
      expires_in: 3600,
      user,
    };
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(authResponse),
    });

    const client = createClient();
    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper(client) });
    await result.current.mutateAsync({ email: user.email, password: "hunter2" });

    expect(client.getQueryData(queryKeys.me)).toEqual(user);

    const cached = JSON.stringify(
      client.getQueryCache().getAll().map((q) => ({ key: q.queryKey, data: q.state.data })),
    );
    expect(cached).not.toContain("SECRET.JWT.TOKEN.VALUE");
    expect(cached).not.toContain("access_token");

    // No web storage anywhere in the app (contract: SPA must not store the token)
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});