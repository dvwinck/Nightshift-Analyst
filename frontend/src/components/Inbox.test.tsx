import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { message } from "../test/fixtures";
import Inbox from "./Inbox";

describe("Inbox", () => {
  it("shows when a message expires, and nothing for messages that never do", () => {
    render(
      <Inbox
        disabled={false}
        onCommand={vi.fn()}
        inbox={[message({ id: "alert-101", due: "00:00" }), message({ id: "chat-12", due: null })]}
      />
    );

    expect(screen.getByText(/due 00:00/)).toBeInTheDocument();
    expect(screen.queryAllByText(/due /)).toHaveLength(1);
  });

  it("names every action button after its verb, message and label (not just 'execute')", () => {
    render(
      <Inbox
        disabled={false}
        onCommand={vi.fn()}
        inbox={[message({ read: true, verbs: [{ verb: "execute", label: "Purge the archive" }] })]}
      />
    );

    expect(screen.getByRole("button", { name: "execute order-773: Purge the archive" })).toBeInTheDocument();
  });

  it("announces unread messages to screen readers", () => {
    render(<Inbox disabled={false} onCommand={vi.fn()} inbox={[message({ read: false })]} />);

    expect(screen.getByText("Unread")).toHaveClass("visually-hidden");
  });
});
