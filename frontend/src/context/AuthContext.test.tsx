import { render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../api/auth";
import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import { AuthProvider } from "./AuthContext";

vi.mock("../api/auth");

const profile = {
  id: "u1",
  email: "a@nightshift.dev",
  username: "analyst",
  is_active: true,
  is_superuser: false,
  is_verified: false,
  created_at: "",
  updated_at: "",
};

const Probe = () => {
  const { isAuthenticated, isLoading, error, token } = useAuth();
  return (
    <div>
      <span data-testid="state">{isLoading ? "loading" : isAuthenticated ? "in" : "out"}</span>
      <span data-testid="token">{token ?? "none"}</span>
      <span data-testid="error">{error ?? ""}</span>
    </div>
  );
};

const renderProvider = () =>
  render(
    <StrictMode>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </StrictMode>
  );

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
});

describe("AuthProvider bootstrap", () => {
  it("starts signed out without a stored token", async () => {
    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("out"));
  });

  it("restores a stored session when the server accepts the token", async () => {
    localStorage.setItem("nightshift_analyst_token", "tok");
    localStorage.setItem("nightshift_analyst_user", JSON.stringify(profile));
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue(profile);
    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("in"));
    expect(screen.getByTestId("token")).toHaveTextContent("tok");
  });

  it("drops the session and says why when the server rejects the token", async () => {
    localStorage.setItem("nightshift_analyst_token", "old");
    localStorage.setItem("nightshift_analyst_user", JSON.stringify(profile));
    vi.mocked(authApi.fetchCurrentUser).mockRejectedValue(new ApiError("Unauthorized", 401));
    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("out"));
    expect(screen.getByTestId("error")).toHaveTextContent("session expired");
    expect(localStorage.getItem("nightshift_analyst_token")).toBeNull();
  });

  it("keeps the session when the server is merely unreachable", async () => {
    localStorage.setItem("nightshift_analyst_token", "tok");
    localStorage.setItem("nightshift_analyst_user", JSON.stringify(profile));
    vi.mocked(authApi.fetchCurrentUser).mockRejectedValue(new ApiError("Cannot reach the server.", 0));
    renderProvider();

    await waitFor(() => expect(screen.getByTestId("error")).toHaveTextContent("Cannot reach"));
    expect(localStorage.getItem("nightshift_analyst_token")).toBe("tok");
    expect(screen.getByTestId("state")).toHaveTextContent("in");
  });
});
