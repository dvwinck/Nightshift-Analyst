import { EventKind, LogEntry } from "../types";

export type Line = {
  id: number;
  kind: EventKind | "command";
  text: string;
};

/** The server logs the shift start as entry 0; it is bookkeeping, not something the player typed. */
const START_SEQ = 0;

type Entry = Pick<LogEntry, "command" | "events"> & { seq?: number };

/** Turn log entries (or a fresh command result) into terminal lines, echoing what was typed. */
export function toLines(entries: Entry[], firstId: number): Line[] {
  const lines: Line[] = [];
  let id = firstId;
  for (const entry of entries) {
    if (entry.seq !== START_SEQ) {
      lines.push({ id: id++, kind: "command", text: `> ${entry.command}` });
    }
    for (const event of entry.events) {
      lines.push({ id: id++, kind: event.kind, text: event.text });
    }
  }
  return lines;
}
