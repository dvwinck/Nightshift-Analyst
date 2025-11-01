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

  if (body instanceof URLSearchParams || body instanceof FormData) {
    requestBody = body;
  } else if (body && typeof body === "object") {
    fetchHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  } else if (typeof body === "string" || body instanceof Blob) {
    requestBody = body;
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
    const message =
      (isJson && (payload as { detail?: string })?.detail) ||
      response.statusText ||
      "Request failed";
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}
