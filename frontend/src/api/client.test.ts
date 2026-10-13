import { describe, expect, it } from "vitest";

import { afterEach, vi } from "vitest";

import { ApiError, NETWORK_ERROR_MESSAGE, errorMessage, request } from "./client";

describe("errorMessage", () => {
  it("uses a string detail as-is", () => {
    expect(errorMessage({ detail: "REGISTER_USER_ALREADY_EXISTS" }, true, "Bad Request")).toBe(
      "REGISTER_USER_ALREADY_EXISTS"
    );
  });

  it("joins FastAPI validation messages instead of printing [object Object]", () => {
    const payload = { detail: [{ msg: "String should have at least 3 characters" }, { msg: "Field required" }] };

    expect(errorMessage(payload, true, "Unprocessable Entity")).toBe(
      "String should have at least 3 characters; Field required"
    );
  });

  it("shows the reason fastapi-users gives for rejected passwords", () => {
    const payload = { detail: { code: "REGISTER_INVALID_PASSWORD", reason: "Password must be at least 8 characters." } };

    expect(errorMessage(payload, true, "Bad Request")).toBe("Password must be at least 8 characters.");
  });

  it("falls back to the status text, then a generic message", () => {
    expect(errorMessage({}, true, "Not Found")).toBe("Not Found");
    expect(errorMessage("html", false, "")).toBe("Request failed");
    expect(errorMessage(null, true, "")).toBe("Request failed");
  });
});


describe("request", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("turns an unreachable server into a readable ApiError instead of 'Failed to fetch'", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const failure = (await request("/x").catch((err) => err)) as ApiError;

    expect(failure).toBeInstanceOf(ApiError);
    expect(failure.message).toBe(NETWORK_ERROR_MESSAGE);
    expect(failure.status).toBe(0);
  });
});
