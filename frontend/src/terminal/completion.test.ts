import { describe, expect, it } from "vitest";

import { message } from "../test/fixtures";
import { complete } from "./completion";

const inbox = [
  message({ id: "order-773", read: true, verbs: [{ verb: "execute", label: "x" }, { verb: "deny", label: "y" }] }),
  message({ id: "order-774", read: false }),
  message({ id: "alert-101", read: true, verbs: [{ verb: "execute", label: "z" }] }),
];

describe("complete", () => {
  it("completes a unique command and adds a space when it takes an argument", () => {
    expect(complete("rea", inbox)).toBe("read ");
    expect(complete("clo", inbox)).toBe("clockout");
  });

  it("completes to the common prefix of ambiguous commands", () => {
    expect(complete("d", inbox)).toBe("de"); // deny, delay
    expect(complete("i", inbox)).toBe("in"); // inbox, investigate
  });

  it("completes message ids for read from every open message", () => {
    expect(complete("read al", inbox)).toBe("read alert-101");
    expect(complete("read order-7", inbox)).toBe("read order-77");
    expect(complete("read ", inbox)).toBe("read ");
  });

  it("only offers messages that were read and allow the verb", () => {
    expect(complete("execute ", inbox)).toBe("execute ");
    expect(complete("deny o", inbox)).toBe("deny order-773");
    expect(complete("deny a", inbox)).toBe("deny a");
  });

  it("leaves unknown input and empty input alone", () => {
    expect(complete("", inbox)).toBe("");
    expect(complete("zzz", inbox)).toBe("zzz");
    expect(complete("status extra", inbox)).toBe("status extra");
  });
});
