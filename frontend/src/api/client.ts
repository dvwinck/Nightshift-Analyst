const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;

type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: BodyInit | Record<string, unknown> | null;
  token?: string | null;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/** FastAPI sends ``detail`` as a string, or as a list of validation problems (HTTP 422). */
export function errorMessage(payload: unknown, isJson: boolean, statusText: string): string {
  const detail = isJson ? (payload as { detail?: unknown } | null)?.detail : undefined;
  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const reason = (detail as { reason?: unknown }).reason;
    if (typeof reason === "string" && reason) return reason;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" ? (item as { msg?: unknown }).msg : null))
      .filter((msg): msg is string => typeof msg === "string");
    if (messages.length > 0) return messages.join("; ");
  }
  return statusText || "Request failed";
}

export async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", headers = {}, body, token, signal } = options;

  const fetchHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };

  let requestBody: BodyInit | undefined;

  if (
    typeof body === "string" ||
    body instanceof URLSearchParams ||
    body instanceof FormData ||
    body instanceof Blob
  ) {
    requestBody = body;
  } else if (body && typeof body === "object") {
    fetchHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }

  if (token) {
    fetchHeaders.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: fetchHeaders,
    body: requestBody,
    signal,
  });

  let payload: unknown;

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  if (isJson) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    throw new ApiError(errorMessage(payload, isJson, response.statusText), response.status, payload);
  }

  return payload as T;
}
