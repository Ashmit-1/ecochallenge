import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ProtectedRoute, PublicOnlyRoute } from "./ProtectedRoute";
import type { User } from "../types";

const testUser: User = {
  id: 1,
  email: "student@campus.edu",
  display_name: "Test Student",
  points_total: 50,
  created_at: "2026-01-01T00:00:00Z",
};

function authResponse(ok: boolean, user: User | null = null) {
  return {
    ok,
    status: ok ? 200 : 401,
    statusText: ok ? "OK" : "Unauthorized",
    json: () => (ok ? Promise.resolve(user) : Promise.resolve({ detail: "Not authenticated" })),
  };
}

function renderWithProviders(ui: ReactNode, initialEntries: string[] = ["/"]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
  });

  it("renders children when authenticated", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(authResponse(true, testUser));

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<div data-testid="login-page" />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div data-testid="protected-content" />
            </ProtectedRoute>
          }
        />
      </Routes>,
      ["/dashboard"],
    );

    expect(await screen.findByTestId("protected-content")).toBeInTheDocument();
    expect(screen.queryByTestId("login-page")).not.toBeInTheDocument();
  });

  it("redirects to /login when unauthenticated", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(authResponse(false));

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<div data-testid="login-page" />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div data-testid="protected-content" />
            </ProtectedRoute>
          }
        />
      </Routes>,
      ["/dashboard"],
    );

    expect(await screen.findByTestId("login-page")).toBeInTheDocument();
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });
});

describe("PublicOnlyRoute", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
  });

  it("renders children when logged out", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(authResponse(false));

    renderWithProviders(
      <Routes>
        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <div data-testid="login-form" />
            </PublicOnlyRoute>
          }
        />
        <Route path="/challenges" element={<div data-testid="challenges-page" />} />
      </Routes>,
      ["/login"],
    );

    expect(await screen.findByTestId("login-form")).toBeInTheDocument();
    expect(screen.queryByTestId("challenges-page")).not.toBeInTheDocument();
  });

  it("redirects to /challenges when already authenticated", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(authResponse(true, testUser));

    renderWithProviders(
      <Routes>
        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <div data-testid="login-form" />
            </PublicOnlyRoute>
          }
        />
        <Route path="/challenges" element={<div data-testid="challenges-page" />} />
      </Routes>,
      ["/login"],
    );

    expect(await screen.findByTestId("challenges-page")).toBeInTheDocument();
    expect(screen.queryByTestId("login-form")).not.toBeInTheDocument();
  });
});