import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../api/shifts";
import { shift } from "../test/fixtures";
import { CommandResult } from "../types";
import { useShift } from "./useShift";

vi.mock("../api/shifts");
const mocked = vi.mocked(api);

beforeEach(() => {
  vi.resetAllMocks();
  mocked.getCurrentShift.mockResolvedValue(shift());
  mocked.getLog.mockResolvedValue([]);
});

describe("useShift", () => {
  it("sends only one request when send is called twice before the first answers", async () => {
    let finish: (value: CommandResult) => void = () => undefined;
    mocked.sendCommand.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const { result } = renderHook(() => useShift("tok", vi.fn()));
    await act(async () => {
      await result.current.load();
    });

    await act(async () => {
      void result.current.send("status");
      void result.current.send("inbox"); // same tick: only the ref guard can stop this one
    });
    finish({ accepted: true, events: [], shift: shift() });
    await waitFor(() => expect(result.current.busy).toBe(false));

    expect(mocked.sendCommand).toHaveBeenCalledTimes(1);
  });

  it("trims commands and ignores blank ones", async () => {
    mocked.sendCommand.mockResolvedValue({ accepted: true, events: [], shift: shift() });
    const { result } = renderHook(() => useShift("tok", vi.fn()));
    await act(async () => {
      await result.current.load();
    });

    await act(async () => {
      await result.current.send("   ");
      await result.current.send("  status  ");
    });

    expect(mocked.sendCommand).toHaveBeenCalledTimes(1);
    expect(mocked.sendCommand).toHaveBeenCalledWith("tok", "status");
  });
});
