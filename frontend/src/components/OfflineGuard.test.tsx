import { describe, it, expect, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { OfflineGuard } from "./OfflineGuard";

function setOnLine(value: boolean) {
  Object.defineProperty(window.navigator, "onLine", {
    configurable: true,
    get: () => value,
  });
}

afterEach(() => {
  setOnLine(true); // restore jsdom default
});

describe("OfflineGuard (contract §8: branded offline screen + retry)", () => {
  it("shows the branded offline screen with a retry button when offline", () => {
    setOnLine(false);

    render(
      <OfflineGuard>
        <div data-testid="app" />
      </OfflineGuard>,
    );

    expect(screen.queryByTestId("app")).not.toBeInTheDocument();
    expect(screen.getByText("You're offline.")).toBeInTheDocument();
    expect(screen.getByText(/come back when you're connected/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("renders children when online", () => {
    setOnLine(true);

    render(
      <OfflineGuard>
        <div data-testid="app" />
      </OfflineGuard>,
    );

    expect(screen.getByTestId("app")).toBeInTheDocument();
    expect(screen.queryByText("You're offline.")).not.toBeInTheDocument();
  });

  it("reacts live to offline and online events", () => {
    setOnLine(true);

    render(
      <OfflineGuard>
        <div data-testid="app" />
      </OfflineGuard>,
    );
    expect(screen.getByTestId("app")).toBeInTheDocument();

    fireEvent(window, new Event("offline"));
    expect(screen.queryByTestId("app")).not.toBeInTheDocument();
    expect(screen.getByText("You're offline.")).toBeInTheDocument();

    fireEvent(window, new Event("online"));
    expect(screen.getByTestId("app")).toBeInTheDocument();
  });
});