import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, ApiError } from "./api";
import * as apiExports from "./api";

describe("api client", () => {
  beforeEach(() => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });
    globalThis.fetch = vi.fn();
  });

  it("sends credentials include on every request", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: "ok" }),
    });

    await api("/health");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("attaches CSRF token on POST requests", async () => {
    document.cookie = "ecochallenge_csrf=test-token-123";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api("/auth/login", { method: "POST", body: "test" });

    const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("test-token-123");
  });

  it("does not attach CSRF token on GET requests", async () => {
    document.cookie = "ecochallenge_csrf=test-token-123";
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api("/challenges");

    const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers as Headers;
    expect(headers.has("X-CSRF-Token")).toBe(false);
  });

  it("sets Content-Type application/json for non-FormData bodies", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api("/auth/me", { method: "PATCH", body: JSON.stringify({ display_name: "x" }) });

    const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("does not set Content-Type for FormData bodies", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({}),
    });

    const form = new FormData();
    form.append("image", new Blob(["test"]), "photo.jpg");
    await api("/challenges/test/submissions", { method: "POST", body: form });

    const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers as Headers;
    expect(headers.has("Content-Type")).toBe(false);
  });

  it("returns undefined for 204 responses", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 204,
    });

    const result = await api("/auth/logout", { method: "POST" });
    expect(result).toBeUndefined();
  });

  it("throws ApiError with detail from JSON response on failure", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Invalid credentials" }),
    });

    await expect(api("/auth/me")).rejects.toThrow(ApiError);
  });

  it("retries once on 403 CSRF error", async () => {
    document.cookie = "ecochallenge_csrf=old-token";
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: "Forbidden",
        json: () => Promise.resolve({ detail: "CSRF token missing or invalid" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1 }),
      });

    const result = await api("/auth/me", { method: "PATCH", body: "{}" });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ id: 1 });
  });
});

describe("401 handling (regression: reload loop guard)", () => {
  beforeEach(() => {
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
    globalThis.fetch = vi.fn();
    apiExports.setUnauthorizedHandler(null);
  });

  afterEach(() => {
    apiExports.setUnauthorizedHandler(null);
  });

  it("notifies the unauthorized handler instead of navigating", async () => {
    const handler = vi.fn();
    apiExports.setUnauthorizedHandler(handler);
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Not authenticated" }),
    });

    await expect(api("/auth/me")).rejects.toThrow(ApiError);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does not notify the handler for non-401 errors", async () => {
    const handler = vi.fn();
    apiExports.setUnauthorizedHandler(handler);
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: "Boom" }),
    });

    await expect(api("/profile")).rejects.toThrow(ApiError);
    expect(handler).not.toHaveBeenCalled();
  });

  it("survives removed handler (no crash after unmount)", async () => {
    apiExports.setUnauthorizedHandler(null);
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Not authenticated" }),
    });

    await expect(api("/auth/me")).rejects.toThrow(ApiError);
  });
});

describe("ApiError", () => {
  it("parses string detail from response", async () => {
    const response = {
      status: 422,
      statusText: "Unprocessable Entity",
      json: () => Promise.resolve({ detail: "Validation failed" }),
    } as Response;

    const err = await ApiError.fromResponse(response);
    expect(err.status).toBe(422);
    expect(err.detail).toBe("Validation failed");
    expect(err.message).toBe("Validation failed");
  });

  it("parses array detail from response", async () => {
    const response = {
      status: 422,
      statusText: "Unprocessable Entity",
      json: () => Promise.resolve({
        detail: [{ msg: "field required" }, { msg: "too short" }],
      }),
    } as Response;

    const err = await ApiError.fromResponse(response);
    expect(err.detail).toBe("field required, too short");
  });

  it("falls back to statusText when JSON parsing fails", async () => {
    const response = {
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not json")),
    } as Response;

    const err = await ApiError.fromResponse(response);
    expect(err.detail).toBe("Internal Server Error");
  });
});

describe("login content-type regression (H1) and contract §5 headers", () => {
  beforeEach(() => {
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
    globalThis.fetch = vi.fn();
  });

  it("preserves an explicit application/x-www-form-urlencoded header instead of clobbering to JSON", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ access_token: "ignored", token_type: "bearer", expires_in: 604800, user: { id: 1 } }),
    });

    await api("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: "s@campus.edu", password: "pw" }).toString(),
    });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/x-www-form-urlencoded");
  });

  it("still defaults to application/json when the caller sets none", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api("/auth/register", { method: "POST", body: JSON.stringify({ email: "a@b.c" }) });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("decodes a CSRF cookie value containing '=' characters intact", async () => {
    const value = "abc=def==";
    document.cookie = `ecochallenge_csrf=${encodeURIComponent(value)}`;
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api("/auth/me", { method: "PATCH", body: "{}" });

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe(value);
  });

  it("reads Retry-After into ApiError.retryAfterSeconds on 429 (contract §5)", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 429,
      statusText: "Too Many Requests",
      headers: { get: (h: string) => (h === "Retry-After" ? "120" : null) },
      json: () => Promise.resolve({ detail: "Cooldown active until tomorrow." }),
    });

    const err = await api("/challenges/x/submissions", { method: "POST", body: new FormData() }).catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).retryAfterSeconds).toBe(120);
    expect((err as ApiError).detail).toContain("Cooldown");
  });
});
