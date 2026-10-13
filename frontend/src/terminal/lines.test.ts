import { describe, expect, it } from "vitest";

import { toLines } from "./lines";

describe("toLines", () => {
  it("echoes typed commands and keeps event kinds", () => {
    const lines = toLines(
      [{ command: "read order-773", events: [{ kind: "message", text: "Purge...", data: {} }] }],
      10
    );

    expect(lines).toEqual([
      { id: 10, kind: "command", text: "> read order-773" },
      { id: 11, kind: "message", text: "Purge..." },
    ]);
  });

  it("does not echo the internal start entry (seq 0)", () => {
    const lines = toLines(
      [{ seq: 0, command: "start", events: [{ kind: "info", text: "NIGHTSHIFT", data: {} }] }],
      1
    );

    expect(lines).toEqual([{ id: 1, kind: "info", text: "NIGHTSHIFT" }]);
  });

  it("still echoes a player who literally typed 'start'", () => {
    const lines = toLines(
      [{ seq: 4, command: "start", events: [{ kind: "error", text: "Unknown command", data: {} }] }],
      1
    );

    expect(lines[0]).toEqual({ id: 1, kind: "command", text: "> start" });
  });

  it("assigns strictly increasing ids across entries", () => {
    const lines = toLines(
      [
        { command: "status", events: [{ kind: "info", text: "a", data: {} }] },
        { command: "inbox", events: [{ kind: "info", text: "b", data: {} }] },
      ],
      5
    );

    expect(lines.map((line) => line.id)).toEqual([5, 6, 7, 8]);
  });
});
