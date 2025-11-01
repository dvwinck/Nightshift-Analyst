import { request } from "./client";
import { Case, CaseCreatePayload, CaseUpdatePayload } from "../types";

export async function getCases(token: string): Promise<Case[]> {
  return request<Case[]>("/cases/", {
    method: "GET",
    token,
  });
}

export async function createCase(
  token: string,
  payload: CaseCreatePayload
): Promise<Case> {
  return request<Case>("/cases/", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function updateCase(
  token: string,
  caseId: string,
  payload: CaseUpdatePayload
): Promise<Case> {
  return request<Case>(`/cases/${caseId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}
