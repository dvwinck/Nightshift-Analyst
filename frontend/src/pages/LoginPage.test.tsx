import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../api/auth";
import { ApiError } from "../api/client";
import { AuthContext } from "../context/AuthContext";
import LoginPage from "./LoginPage";

vi.mock("../api/auth");

const login = vi.fn();

const renderPage = (error: string | null = null) =>
  render(
    <MemoryRouter>
      <AuthContext.Provider
        value={{
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          error,
          login,
          logout: vi.fn(),
          refreshUser: vi.fn(),
        }}
      >
        <LoginPage />
      </AuthContext.Provider>
    </MemoryRouter>
  );

beforeEach(() => {
  vi.resetAllMocks();
});

describe("LoginPage", () => {
  it("signs in with the email (the API authenticates by email, not username)", async () => {
    login.mockResolvedValue(undefined);
    renderPage();

    await userEvent.type(screen.getByLabelText("Email"), "a@nightshift.dev");
    await userEvent.type(screen.getByLabelText("Password"), "correct-horse");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(login).toHaveBeenCalledWith({ username: "a@nightshift.dev", password: "correct-horse" });
  });

  it("translates API error codes into readable messages", async () => {
    login.mockRejectedValue(new ApiError("LOGIN_BAD_CREDENTIALS", 400));
    renderPage();

    await userEvent.type(screen.getByLabelText("Email"), "a@nightshift.dev");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong email or password.");
  });

  it("registers, then signs in with the same credentials", async () => {
    vi.mocked(authApi.register).mockResolvedValue({} as never);
    login.mockResolvedValue(undefined);
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: "Create one" }));
    await userEvent.type(screen.getByLabelText("Email"), "new@nightshift.dev");
    await userEvent.type(screen.getByLabelText(/Username/), "newbie");
    await userEvent.type(screen.getByLabelText(/Password/), "long-enough-pw");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(login).toHaveBeenCalled());
    expect(authApi.register).toHaveBeenCalledWith({
      email: "new@nightshift.dev",
      username: "newbie",
      password: "long-enough-pw",
    });
    expect(login).toHaveBeenCalledWith({ username: "new@nightshift.dev", password: "long-enough-pw" });
  });

  it("shows the session-expired message handed over by the auth context", () => {
    renderPage("Your session expired. Please sign in again.");

    expect(screen.getByRole("alert")).toHaveTextContent("session expired");
  });
});
