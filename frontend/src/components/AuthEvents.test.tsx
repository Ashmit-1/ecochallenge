import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthEvents } from "./AuthEvents";
import { api, ApiError, setUnauthorizedHandler } from "../lib/api";

// AuthEvents decides whether to redirect by reading window.location.pathname
// (the document URL), then redirects through React Router. We spy on
// useNavigate so the test can assert "navigation happened" / "did NOT happen"
// directly, independent of what the DOM looks like.
const { navigateSpy } = vi.hoisted(() => ({ navigateSpy: vi.fn() }));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => {
      const navigate = actual.useNavigate();
      return ((to: string, options?: { replace?: boolean }) => {
        navigateSpy(to, options);
        return navigate(to, options);
      }) as typeof navigate;
    },
  };
});

// Renders window.location.pathname (the document URL) so tests can prove which
// path the handler inspected at call time.
function PathBadge() {
  return <span data-testid="doc-path">{window.location.pathname}</span>;
}

function renderApp(initialEntries: string[], initialDocumentPath: string) {
  // MemoryRouter navigation never touches the document URL, so drive
  // window.location to the same path the router starts on (in the real app
  // BrowserRouter keeps the two in sync).
  window.history.pushState({}, "", initialDocumentPath);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthEvents />
        <Routes>
          <Route
            path="/protected"
            element={
              <div data-testid="protected-page">
                <PathBadge />
              </div>
            }
          />
          <Route
            path="/login"
            element={
              <div data-testid="login-page">
                <PathBadge />
              </div>
            }
          />
          <Route
            path="/register"
            element={
              <div data-testid="register-page">
                <PathBadge />
              </div>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mock401() {
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
    ok: false,
    status: 401,
    statusText: "Unauthorized",
    json: () => Promise.resolve({ detail: "Not authenticated" }),
  });
}

// Flush pending microtasks + at least one macrotask turn inside React's act,
// so router state updates scheduled by the 401 handler are committed.
async function flushRender(ms = 25) {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, ms));
  });
}

// Fires a 401 through the api client. The unauthorized handler runs
// synchronously inside api() and may update router state, so keep it in act().
async function trigger401() {
  await act(async () => {
    await expect(api("/auth/me")).rejects.toBeInstanceOf(ApiError);
  });
}

describe("AuthEvents — 401 handler", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    Object.defineProperty(document, "cookie", { writable: true, value: "" });
    navigateSpy.mockClear();
    setUnauthorizedHandler(null);
  });

  afterEach(() => {
    setUnauthorizedHandler(null);
    window.history.pushState({}, "", "/");
    vi.clearAllMocks();
  });

  it("routes to /login when a 401 arrives on a protected path", async () => {
    const { container } = renderApp(["/protected"], "/protected");

    expect(screen.getByTestId("protected-page")).toBeInTheDocument();
    expect(screen.getByTestId("doc-path")).toHaveTextContent("/protected");

    mock401();
    await trigger401();

    // Handler ran synchronously inside api(); flush the router update.
    await waitFor(() => {
      expect(screen.getByTestId("login-page")).toBeInTheDocument();
    });
    await flushRender();

    expect(navigateSpy).toHaveBeenCalledWith("/login", { replace: true });
    expect(screen.queryByTestId("protected-page")).not.toBeInTheDocument();
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(container).toBeTruthy();
  });

  it("does not navigate or loop when the current path is already /login", async () => {
    renderApp(["/login"], "/login");

    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(screen.getByTestId("doc-path")).toHaveTextContent("/login");
    const loginNodeBefore = screen.getByTestId("login-page");

    mock401();
    // Trigger the 401 twice: a second signal must not cause a re-navigation.
    await trigger401();
    await trigger401();
    await flushRender(50);

    expect(navigateSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    // Same DOM node => never unmounted/remounted by a routing loop
    expect(screen.getByTestId("login-page")).toBe(loginNodeBefore);
    expect(screen.queryByTestId("protected-page")).not.toBeInTheDocument();
    expect(screen.getByTestId("doc-path")).toHaveTextContent("/login");
  });

  it("does not navigate when the current path is already /register", async () => {
    renderApp(["/register"], "/register");

    expect(screen.getByTestId("register-page")).toBeInTheDocument();

    mock401();
    await trigger401();
    await flushRender(50);

    expect(navigateSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("register-page")).toBeInTheDocument();
    expect(screen.queryByTestId("login-page")).not.toBeInTheDocument();
    expect(screen.queryByTestId("protected-page")).not.toBeInTheDocument();
  });
});