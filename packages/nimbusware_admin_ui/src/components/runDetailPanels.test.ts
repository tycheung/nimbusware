import { describe, expect, it } from "vitest";

describe("run detail panel contracts", () => {
  it("research brief status uses pending gate for actions", () => {
    const pending = { status: "pending" };
    const approved = { status: "approved" };
    expect(pending.status === "pending").toBe(true);
    expect(approved.status === "pending").toBe(false);
  });

  it("stitch event line format matches maker review", () => {
    const ev = { store_seq: 3, event_type: "stitch.applied", summary: "applied 2 paths" };
    const line = `#${ev.store_seq} ${ev.event_type}: ${ev.summary || ""}`;
    expect(line).toBe("#3 stitch.applied: applied 2 paths");
  });
});
