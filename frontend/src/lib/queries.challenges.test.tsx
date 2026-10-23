import { describe, it, expect, beforeEach, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { challengeDetailQuery, submissionsQuery, leaderboardQuery, queryKeys } from "./queries";

// Invokes a queryOptions' queryFn with a full QueryFunctionContext, while the
// global fetch is mocked, so we can assert the exact HTTP URL the factory
// produces (contract §4).
type QueryFunctionRun = (ctx: {
  client: QueryClient;
  queryKey: readonly unknown[];
  signal: AbortSignal;
  meta?: unknown;
}) => Promise<unknown>;

async function runQueryFn(options: {
  queryKey: readonly unknown[];
  queryFn?: unknown;
}): Promise<unknown> {
  if (typeof options.queryFn !== "function") {
    throw new Error("query factory returned no queryFn");
  }
  const fn = options.queryFn as QueryFunctionRun;
  return fn({
    client: new QueryClient(),
    queryKey: options.queryKey,
    signal: new AbortController().signal,
    meta: undefined,
  });
}

function mockOk(body: unknown) {
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  });
}

function fetchUrl(index = 0): string {
  return String((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[index][0]);
}

beforeEach(() => {
  globalThis.fetch = vi.fn();
  Object.defineProperty(document, "cookie", { writable: true, value: "" });
});

describe("challengeDetailQuery (cache-poisoning key guard)", () => {
  it("scopes keys as [challenges, detail, slug] under the challenges root", () => {
    expect(challengeDetailQuery("bike-to-campus").queryKey).toEqual([
      "challenges",
      "detail",
      "bike-to-campus",
    ]);
    // Invalidation target used by mutations must be a key prefix
    expect(challengeDetailQuery("bike-to-campus").queryKey[0]).toBe(
      queryKeys.challenges.all[0],
    );
    expect(queryKeys.challenges.all).toEqual(["challenges"]);
  });

  it("keeps distinct slugs in distinct cache entries and is stable per slug", () => {
    const a1 = challengeDetailQuery("bike-to-campus").queryKey;
    const a2 = challengeDetailQuery("bike-to-campus").queryKey;
    const b = challengeDetailQuery("plant-a-tree").queryKey;

    expect(a1).toEqual(a2);
    expect(a1).not.toEqual(b);
    expect(queryKeys.challenges.list()).not.toEqual(a1);
  });

  it("fetches the percent-encoded slug while keeping the raw slug in the key", async () => {
    mockOk({ id: 1, slug: "bike to campus" });

    const options = challengeDetailQuery("bike to campus");
    const data = await runQueryFn(options);

    expect(fetchUrl()).toBe(`/api/v1/challenges/${encodeURIComponent("bike to campus")}`);
    expect(data).toEqual({ id: 1, slug: "bike to campus" });
    expect(options.queryKey).toHaveLength(3);
  });
});

describe("submissionsQuery (limit/offset factory)", () => {
  it("builds the key as [submissions, list, params] under the submissions root", () => {
    expect(submissionsQuery({ limit: 5, offset: 20 }).queryKey).toEqual([
      "submissions",
      "list",
      { limit: 5, offset: 20 },
    ]);
    expect(queryKeys.submissions.all).toEqual(["submissions"]);
    expect(submissionsQuery({ limit: 5, offset: 20 }).queryKey[0]).toBe(
      queryKeys.submissions.all[0],
    );
  });

  it("differs per page so pagination cannot poison other pages' cache", () => {
    const page1 = submissionsQuery({ limit: 5, offset: 0 }).queryKey;
    const page2 = submissionsQuery({ limit: 5, offset: 5 }).queryKey;
    expect(page1).not.toEqual(page2);
  });

  it("appends limit and offset as query params", async () => {
    mockOk([]);
    await runQueryFn(submissionsQuery({ limit: 5, offset: 20 }));
    expect(fetchUrl()).toBe("/api/v1/submissions?limit=5&offset=20");
  });

  it("omits the query string entirely when no params are given", async () => {
    mockOk([]);
    await runQueryFn(submissionsQuery());
    expect(fetchUrl()).toBe("/api/v1/submissions");
    expect(fetchUrl()).not.toContain("?");
  });
});

describe("leaderboardQuery (limit/offset factory)", () => {
  it("builds the key as [leaderboard, params] and differs per page", () => {
    expect(leaderboardQuery({ limit: 10, offset: 20 }).queryKey).toEqual([
      "leaderboard",
      { limit: 10, offset: 20 },
    ]);
    expect(leaderboardQuery({ limit: 10, offset: 20 }).queryKey).not.toEqual(
      leaderboardQuery({ limit: 10, offset: 40 }).queryKey,
    );
    // Prefix used by useSubmitEvidence invalidation must still match these keys
    expect(leaderboardQuery().queryKey[0]).toBe("leaderboard");
  });

  it("fetches /api/v1/leaderboard?limit=10&offset=20", async () => {
    mockOk({ entries: [], total_participants: 0, current_user_rank: 0 });
    const data = await runQueryFn(leaderboardQuery({ limit: 10, offset: 20 }));

    expect(fetchUrl()).toBe("/api/v1/leaderboard?limit=10&offset=20");
    expect(data).toEqual({ entries: [], total_participants: 0, current_user_rank: 0 });
  });

  it("fetches /api/v1/leaderboard with no query string when unpaginated", async () => {
    mockOk({ entries: [], total_participants: 0, current_user_rank: 0 });
    await runQueryFn(leaderboardQuery());

    expect(fetchUrl()).toBe("/api/v1/leaderboard");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/leaderboard",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});