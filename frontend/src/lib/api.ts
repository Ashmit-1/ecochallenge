// lib/api.ts — the one place that talks to the backend
// Contract: frontend-backend-contract.md §2

import type { User } from "../types";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: string;
  /** Seconds from a Retry-After header (contract §5, 429 responses). */
  retryAfterSeconds: number | null;

  constructor(status: number, detail: string, retryAfterSeconds: number | null = null) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfterSeconds = retryAfterSeconds;
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
    const retryAfterHeader = response.headers?.get?.("Retry-After");
    const parsedRetryAfter = Number(retryAfterHeader);
    const retryAfterSeconds =
      retryAfterHeader != null && Number.isFinite(parsedRetryAfter)
        ? parsedRetryAfter
        : null;
    return new ApiError(response.status, detail, retryAfterSeconds);
  }
}

function csrfToken(): string {
  const row = document.cookie
    .split("; ")
    .find((r) => r.startsWith("ecochallenge_csrf="));
  // Slice after the prefix — splitting on "=" would truncate values containing "="
  return row ? decodeURIComponent(row.slice("ecochallenge_csrf=".length)) : "";
}

// --- 401 handling (contract §2.4: clear auth state and route to /login) ---
// The fetch layer NEVER navigates: a hard `window.location` assignment here
// caused an infinite full-page reload loop on /login (each mount 401s). The
// app shell registers a handler that redirects through React Router instead,
// with a same-path guard so it can never loop.

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(fn: UnauthorizedHandler | null): void {
  unauthorizedHandler = fn;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);

  // Default to JSON, but never clobber an explicit caller header: login sends
  // application/x-www-form-urlencoded (OAuth2 form, contract §2) and overwriting
  // that made every SPA login fail with 422.
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
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

    // 401 → notify the app shell; it clears auth state and routes to /login
    // through the router (never a hard navigation — that caused reload loops).
    if (err.status === 401) {
      unauthorizedHandler?.();
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
