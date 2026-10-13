import { EventKind, GameEvent, LogEntry } from "../types";

export type Line = {
  id: number;
  kind: EventKind | "command";
  text: string;
};

/** Internal bookkeeping command the server logs when a shift starts; never echoed as input. */
const START_COMMAND = "start";

type Entry = Pick<LogEntry, "command" | "events">;

/** Turn log entries (or a fresh command result) into terminal lines, echoing what was typed. */
export function toLines(entries: Entry[], firstId: number): Line[] {
  const lines: Line[] = [];
  let id = firstId;
  for (const entry of entries) {
    if (entry.command !== START_COMMAND) {
      lines.push({ id: id++, kind: "command", text: `> ${entry.command}` });
    }
    for (const event of entry.events as GameEvent[]) {
      lines.push({ id: id++, kind: event.kind, text: event.text });
    }
  }
  return lines;
}
