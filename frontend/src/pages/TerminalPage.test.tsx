import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import * as api from "../api/shifts";
import { AuthContext } from "../context/AuthContext";
import { message, shift, view } from "../test/fixtures";
import { CommandResult, GameEvent, LogEntry } from "../types";
import TerminalPage from "./TerminalPage";

vi.mock("../api/shifts");

const mocked = vi.mocked(api);
const logout = vi.fn();

const intro: LogEntry = {
  seq: 0,
  command: "start",
  accepted: true,
  created_at: "",
  events: [{ kind: "info", text: "NIGHTSHIFT v0.1 // ANALYST CONSOLE", data: {} }],
};

const result = (events: GameEvent[], viewOverrides = {}, accepted = true): CommandResult => ({
  accepted,
  events,
  shift: shift(viewOverrides),
});

const renderPage = () =>
  render(
    <AuthContext.Provider
      value={{
        user: null,
        token: "tok",
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: vi.fn(),
        logout,
        refreshUser: vi.fn(),
      }}
    >
      <TerminalPage />
    </AuthContext.Provider>
  );

beforeEach(() => {
  vi.resetAllMocks();
  mocked.getCurrentShift.mockResolvedValue(shift());
  mocked.getLog.mockResolvedValue([intro]);
});

describe("TerminalPage", () => {
  it("restores the clock, inbox and scrollback of the current shift", async () => {
    renderPage();

    expect(await screen.findByText("22:00")).toBeInTheDocument();
    expect(screen.getByText("NIGHTSHIFT v0.1 // ANALYST CONSOLE")).toBeInTheDocument();
    expect(screen.getByText(/DIRECTORATE: Purge archive/)).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Ethical" })).toHaveAttribute("aria-valuenow", "50");
  });

  it("offers to start a shift when none exists, then loads it", async () => {
    mocked.getCurrentShift.mockRejectedValueOnce(new ApiError("No shift yet", 404));
    mocked.startShift.mockResolvedValue(shift());
    mocked.getCurrentShift.mockResolvedValue(shift());
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Start shift" }));

    expect(mocked.startShift).toHaveBeenCalledWith("tok");
    expect(await screen.findByText("22:00")).toBeInTheDocument();
  });

  it("sends the typed command, echoes it, shows events and refreshes the HUD", async () => {
    mocked.sendCommand.mockResolvedValue(
      result([{ kind: "message", text: "Purge archive 77-B before 03:00\nBy order of the Director", data: {} }], {
        clock: 2,
        clock_label: "22:02",
        inbox: [message({ read: true, body: "b", verbs: [{ verb: "execute", label: "Purge" }] })],
      })
    );
    renderPage();
    const input = await screen.findByLabelText("Command");

    await userEvent.type(input, "READ order-773{Enter}");

    expect(mocked.sendCommand).toHaveBeenCalledWith("tok", "READ order-773");
    expect(await screen.findByText("> READ order-773")).toBeInTheDocument();
    expect(screen.getByText(/By order of the Director/)).toBeInTheDocument();
    expect(screen.getByText("22:02")).toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("renders rejected-command errors in the error style and keeps the console usable", async () => {
    mocked.sendCommand.mockResolvedValue(
      result([{ kind: "error", text: "Read order-773 before acting on it.", data: {} }], {}, false)
    );
    renderPage();

    await userEvent.type(await screen.findByLabelText("Command"), "execute order-773{Enter}");

    const error = await screen.findByText("Read order-773 before acting on it.");
    expect(error).toHaveClass("line-error");
    expect(screen.getByLabelText("Command")).toBeEnabled();
  });

  it("blocks a second submit while a command is in flight", async () => {
    let finish: (value: CommandResult) => void = () => undefined;
    mocked.sendCommand.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    renderPage();
    const input = await screen.findByLabelText("Command");

    await userEvent.type(input, "status{Enter}");
    expect(input).toBeDisabled();
    await userEvent.type(input, "inbox{Enter}");
    expect(mocked.sendCommand).toHaveBeenCalledTimes(1);

    finish(result([{ kind: "info", text: "ok", data: {} }]));
    await waitFor(() => expect(input).toBeEnabled());
  });

  it("recalls previous commands with the arrow keys and completes with Tab", async () => {
    mocked.sendCommand.mockResolvedValue(result([{ kind: "info", text: "ok", data: {} }]));
    renderPage();
    const input = await screen.findByLabelText("Command");

    await userEvent.type(input, "status{Enter}");
    await waitFor(() => expect(input).toBeEnabled());
    await userEvent.type(input, "{ArrowUp}");
    expect(input).toHaveValue("status");

    await userEvent.clear(input);
    await userEvent.type(input, "rea{Tab}");
    expect(input).toHaveValue("read ");
  });

  it("sends a command when an inbox button is clicked", async () => {
    mocked.sendCommand.mockResolvedValue(result([{ kind: "info", text: "ok", data: {} }]));
    renderPage();
    const inbox = within(await screen.findByRole("region", { name: "Inbox" }));

    await userEvent.click(inbox.getAllByRole("button", { name: "read" })[0]);

    expect(mocked.sendCommand).toHaveBeenCalledWith("tok", "read order-773");
  });

  it("shows the ending, removes the input and lets the player start a new shift", async () => {
    mocked.getCurrentShift.mockResolvedValue(
      shift({ ending: { id: "daylight", title: "Daylight", text: "The press desk runs it." } })
    );
    renderPage();

    expect(await screen.findByText("Daylight")).toBeInTheDocument();
    expect(screen.queryByLabelText("Command")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start new shift" })).toBeInTheDocument();
  });

  it("logs out when the token is rejected", async () => {
    mocked.sendCommand.mockRejectedValue(new ApiError("Unauthorized", 401));
    renderPage();

    await userEvent.type(await screen.findByLabelText("Command"), "status{Enter}");

    await waitFor(() => expect(logout).toHaveBeenCalled());
  });

  it("reloads the shift when another window changed it (409)", async () => {
    mocked.sendCommand.mockRejectedValue(new ApiError("Shift changed; retry the command.", 409));
    renderPage();

    await userEvent.type(await screen.findByLabelText("Command"), "status{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent("changed in another window");
    await waitFor(() => expect(mocked.getCurrentShift).toHaveBeenCalledTimes(2));
  });

  it("shows a retry button when the shift cannot be loaded", async () => {
    mocked.getCurrentShift.mockRejectedValueOnce(new Error("Network down"));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Network down");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("22:00")).toBeInTheDocument();
  });

  it("does not crash on an empty inbox", async () => {
    mocked.getCurrentShift.mockResolvedValue(shift({ inbox: [] }));
    renderPage();

    expect(await screen.findByText(/Nothing waiting/)).toBeInTheDocument();
    expect(view().inbox.length).toBe(2);
  });
});
