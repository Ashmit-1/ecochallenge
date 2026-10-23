import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, ApiError } from "./api";

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
