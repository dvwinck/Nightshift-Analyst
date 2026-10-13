export type User = {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
};

export type EventKind = "info" | "message" | "outcome" | "timeout" | "error" | "ending";

export type GameEvent = {
  kind: EventKind;
  text: string;
  data: Record<string, unknown>;
};

export type VerbView = { verb: string; label: string };

export type MessageView = {
  id: string;
  category: "order" | "alert" | "intel" | "chat";
  priority: number;
  sender: string;
  title: string;
  read: boolean;
  /** Wall-clock time (e.g. "00:30") after which the message expires, if it ever does. */
  due: string | null;
  body: string | null;
  verbs: VerbView[];
};

export type MetricsView = {
  technical: number;
  ethical: number;
  political: number;
  fatigue: number;
};

export type EndingView = { id: string; title: string; text: string };

export type ShiftView = {
  clock: number;
  clock_label: string;
  remaining_minutes: number;
  metrics: MetricsView;
  inbox: MessageView[];
  ending: EndingView | null;
};

export type Shift = { id: string; started_at: string; view: ShiftView };

export type CommandResult = { accepted: boolean; events: GameEvent[]; shift: Shift };

export type LogEntry = {
  seq: number;
  command: string;
  accepted: boolean;
  events: GameEvent[];
  created_at: string;
};
