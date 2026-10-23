// lib/api.ts — the one place that talks to the backend
// Contract: frontend-backend-contract.md §2

import type { User } from "../types";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  static async fromResponse(response: Response): Promise<ApiError> {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail.map((e: Record<string, unknown>) => e.msg ?? JSON.stringify(e)).join(", ");
      }
    } catch {
      // not JSON — keep statusText
    }
    return new ApiError(response.status, detail);
  }
}

function csrfToken(): string {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith("ecochallenge_csrf="));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);

  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", csrfToken());
  }

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const err = await ApiError.fromResponse(response);

    // 401 → clear auth state and redirect to login
    if (err.status === 401) {
      window.location.href = "/login";
      throw err;
    }

    // 403 CSRF → retry once with fresh cookie
    if (err.status === 403 && err.detail.toLowerCase().includes("csrf")) {
      headers.set("X-CSRF-Token", csrfToken());
      const retry = await fetch(`${BASE}${path}`, {
        ...init,
        method,
        headers,
        credentials: "include",
      });
      if (!retry.ok) {
        // Reload on second failure
        window.location.reload();
        throw await ApiError.fromResponse(retry);
      }
      return retry.status === 204 ? (undefined as T) : ((await retry.json()) as T);
    }

    throw err;
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

// --- Auth helpers ---

export async function register(email: string, password: string, display_name: string) {
  return api<{ access_token: string; token_type: string; expires_in: number; user: User }>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    },
  );
}

export async function login(email: string, password: string) {
  return api<{ access_token: string; token_type: string; expires_in: number; user: User }>(
    "/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    },
  );
}

export async function logout() {
  return api<void>("/auth/logout", { method: "POST" });
}

export async function getMe() {
  return api<User>("/auth/me");
}

export async function updateDisplayName(display_name: string) {
  return api<User>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify({ display_name }),
  });
}

// --- Load evidence photo (contract §6) ---

export async function loadEvidence(imageUrl: string): Promise<string> {
  const response = await fetch(imageUrl, { credentials: "include" });
  if (!response.ok) throw new Error("Could not load photo");
  return URL.createObjectURL(await response.blob());
}
