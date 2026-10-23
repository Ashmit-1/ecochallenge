// lib/queries.ts — TanStack Query keys, fetchers, and hooks
// Contract: frontend-backend-contract.md §4

import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  ChallengeDetail,
  ChallengeSummary,
  HealthResponse,
  Leaderboard,
  Meta,
  Profile,
  Submission,
  SubmissionResult,
  User,
} from "../types";

// --- Query key factory ---

export const queryKeys = {
  health: ["health"] as const,
  meta: ["meta"] as const,
  me: ["auth", "me"] as const,
  challenges: {
    all: ["challenges"] as const,
    list: () => [...queryKeys.challenges.all, "list"] as const,
    detail: (slug: string) => [...queryKeys.challenges.all, "detail", slug] as const,
  },
  submissions: {
    all: ["submissions"] as const,
    list: (params?: { limit?: number; offset?: number }) =>
      [...queryKeys.submissions.all, "list", params] as const,
    detail: (id: number) => [...queryKeys.submissions.all, "detail", id] as const,
  },
  profile: ["profile"] as const,
  leaderboard: (params?: { limit?: number; offset?: number }) =>
    ["leaderboard", params] as const,
};

// --- Query options (for prefetching or useQuery) ---

export const healthQuery = queryOptions({
  queryKey: queryKeys.health,
  queryFn: () => api<HealthResponse>("/health"),
  staleTime: 30_000,
});

export const metaQuery = queryOptions({
  queryKey: queryKeys.meta,
  queryFn: () => api<Meta>("/meta"),
  staleTime: 5 * 60_000,
});

export const meQuery = queryOptions({
  queryKey: queryKeys.me,
  queryFn: () => api<User>("/auth/me"),
  retry: false,
  staleTime: 5 * 60_000,
});

export const challengesQuery = queryOptions({
  queryKey: queryKeys.challenges.list(),
  queryFn: () => api<ChallengeSummary[]>("/challenges"),
  staleTime: 60_000,
});

export function challengeDetailQuery(slug: string) {
  return queryOptions({
    queryKey: queryKeys.challenges.detail(slug),
    queryFn: () => api<ChallengeDetail>(`/challenges/${encodeURIComponent(slug)}`),
    staleTime: 60_000,
  });
}

export function submissionsQuery(params?: { limit?: number; offset?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return queryOptions({
    queryKey: queryKeys.submissions.list(params),
    queryFn: () => api<Submission[]>(`/submissions${qs ? `?${qs}` : ""}`),
    staleTime: 30_000,
  });
}

export const profileQuery = queryOptions({
  queryKey: queryKeys.profile,
  queryFn: () => api<Profile>("/profile"),
  staleTime: 30_000,
});

export function leaderboardQuery(params?: { limit?: number; offset?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return queryOptions({
    queryKey: queryKeys.leaderboard(params),
    queryFn: () => api<Leaderboard>(`/leaderboard${qs ? `?${qs}` : ""}`),
    staleTime: 30_000,
  });
}

// --- Mutations ---

export function useSubmitEvidence(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File): Promise<SubmissionResult> => {
      const form = new FormData();
      form.append("image", file);
      return api<SubmissionResult>(`/challenges/${encodeURIComponent(slug)}/submissions`, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: (data) => {
      // Update profile cache directly from submission response (contract §7)
      qc.setQueryData(queryKeys.profile, data.profile);
      // Invalidate challenges to refresh can_submit / cooldown state
      qc.invalidateQueries({ queryKey: queryKeys.challenges.all });
      // Invalidate submissions list
      qc.invalidateQueries({ queryKey: queryKeys.submissions.all });
      // Invalidate leaderboard
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      // Contract §8: logout must clear TanStack Query caches
      qc.clear();
    },
  });
}

export function useUpdateDisplayName() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (display_name: string) =>
      api<User>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ display_name }),
      }),
    onSuccess: (user) => {
      qc.setQueryData(queryKeys.me, user);
      qc.invalidateQueries({ queryKey: queryKeys.profile });
    },
  });
}