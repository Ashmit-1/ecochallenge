// lib/queries.ts — TanStack Query keys, fetchers, and hooks
// Contract: frontend-backend-contract.md §4

import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  AuthResponse,
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
  if (params?.limit != null) searchParams.set("limit", String(params.limit));
  if (params?.offset != null) searchParams.set("offset", String(params.offset));
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
  if (params?.limit != null) searchParams.set("limit", String(params.limit));
  if (params?.offset != null) searchParams.set("offset", String(params.offset));
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
      // Keep the header points chip in sync with the server-returned total (contract §7:
      // points come from the response profile — this mirrors it into `me`, never adds optimistically)
      qc.setQueryData(queryKeys.me, (prev: User | undefined) =>
        prev ? { ...prev, points_total: data.profile.points_total } : prev,
      );
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
// --- Convenience hooks (useQuery wrappers) ---

export function useMe() {
  return useQuery(meQuery);
}

export function useChallenges() {
  return useQuery(challengesQuery);
}

export function useChallengeDetail(slug: string) {
  return useQuery({
    ...challengeDetailQuery(slug),
    enabled: !!slug,
  });
}

export function useProfile() {
  return useQuery(profileQuery);
}

export function useSubmissions(params?: { limit?: number; offset?: number }) {
  return useQuery(submissionsQuery(params));
}

export function useLeaderboard(params?: { limit?: number; offset?: number }) {
  return useQuery(leaderboardQuery(params));
}

export function useMeta() {
  return useQuery(metaQuery);
}

// --- Auth mutations ---

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => {
      const body = new URLSearchParams({ username: email, password });
      return api<AuthResponse>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });
    },
    onSuccess: (data) => {
      // Contract: never store access_token; cache user from /auth/me
      qc.setQueryData(queryKeys.me, data.user);
    },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password, display_name }: { email: string; password: string; display_name: string }) =>
      api<AuthResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name }),
      }),
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.me, data.user);
    },
  });
}
