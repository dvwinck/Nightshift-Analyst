import { MessageView, Shift, ShiftView } from "../types";

export const message = (overrides: Partial<MessageView> = {}): MessageView => ({
  id: "order-773",
  category: "order",
  priority: 4,
  sender: "DIRECTORATE",
  title: "Purge archive 77-B before 03:00",
  read: false,
  body: null,
  verbs: [],
  ...overrides,
});

export const view = (overrides: Partial<ShiftView> = {}): ShiftView => ({
  clock: 0,
  clock_label: "22:00",
  remaining_minutes: 480,
  metrics: { technical: 50, ethical: 50, political: 50, fatigue: 0 },
  inbox: [message(), message({ id: "alert-101", priority: 2, sender: "SYSMON", title: "Log rotation failed" })],
  ending: null,
  ...overrides,
});

export const shift = (overrides: Partial<ShiftView> = {}): Shift => ({
  id: "shift-1",
  started_at: "2026-10-13T00:00:00",
  view: view(overrides),
});
