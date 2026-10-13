import { useCallback, useRef, useState } from "react";

import { getCurrentShift, getLog, sendCommand, startShift } from "../api/shifts";
import { ApiError } from "../api/client";
import { Line, toLines } from "../terminal/lines";
import { Shift } from "../types";

export type ShiftStatus = "loading" | "none" | "ready" | "error";

/**
 * Owns the shift on the client: the latest server view plus the terminal scrollback.
 * The server is authoritative: this hook only sends commands and renders what comes back.
 */
export function useShift(token: string | null, onUnauthorized: () => void) {
  const [shift, setShift] = useState<Shift | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [status, setStatus] = useState<ShiftStatus>("loading");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nextId = useRef(1);
  const inFlight = useRef(false);

  const fail = useCallback(
    (err: unknown, fallback: string) => {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : fallback);
    },
    [onUnauthorized]
  );

  const replaceScrollback = useCallback((next: Line[]) => {
    nextId.current = next.length + 1;
    setLines(next);
  }, []);

  /** Fetch the current shift and replay its log. Resolves to whether the shift is now loaded. */
  const load = useCallback(async (): Promise<boolean> => {
    if (!token) return false;
    setStatus("loading");
    setError(null);
    try {
      const current = await getCurrentShift(token);
      const log = await getLog(token);
      replaceScrollback(toLines(log, 1));
      setShift(current);
      setStatus("ready");
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setShift(null);
        replaceScrollback([]);
        setStatus("none");
        return true;
      }
      setStatus("error");
      fail(err, "Unable to load your shift.");
      return false;
    }
  }, [token, fail, replaceScrollback]);

  const start = useCallback(async () => {
    if (!token || inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await startShift(token);
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // A shift is already running (another tab, or a double click): just show it.
        await load();
      } else {
        fail(err, "Unable to start a shift.");
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, [token, load, fail]);

  /** Send a command. Resolves to whether the server processed it (so the input can be restored). */
  const send = useCallback(
    async (command: string): Promise<boolean> => {
      const trimmed = command.trim();
      if (!token || !trimmed || inFlight.current) return false;
      inFlight.current = true;
      setBusy(true);
      setError(null);
      try {
        const result = await sendCommand(token, trimmed);
        const added = toLines([{ command: trimmed, events: result.events }], nextId.current);
        nextId.current += added.length;
        setLines((previous) => [...previous, ...added]);
        setShift(result.shift);
        return true;
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          inFlight.current = false;
          setBusy(false);
          const reloaded = await load(); // load() clears the error, so announce afterwards
          if (reloaded) setError("The shift changed in another window. Reloaded.");
          return false;
        }
        fail(err, "Command failed. Try again.");
        return false;
      } finally {
        inFlight.current = false;
        setBusy(false);
      }
    },
    [token, fail, load]
  );

  return { shift, lines, status, busy, error, load, start, send };
}
