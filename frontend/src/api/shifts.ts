import { request } from "./client";
import { CommandResult, LogEntry, Shift } from "../types";

export async function startShift(token: string): Promise<Shift> {
  return request<Shift>("/shifts/", { method: "POST", token });
}

export async function getCurrentShift(token: string): Promise<Shift> {
  return request<Shift>("/shifts/current", { token });
}

export async function sendCommand(token: string, command: string): Promise<CommandResult> {
  return request<CommandResult>("/shifts/current/commands", {
    method: "POST",
    token,
    body: { command },
  });
}

export async function getLog(token: string, limit = 200): Promise<LogEntry[]> {
  return request<LogEntry[]>(`/shifts/current/log?limit=${limit}`, { token });
}
