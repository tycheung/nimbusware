import { describe, expect, it } from "vitest";
import {
  buildRunsQuery,
  decodeRunListCursor,
  encodeRunListCursor,
  filtersFromSearch,
} from "./runListCursor";

describe("runListCursor", () => {
  it("round-trips cursor", () => {
    const runId = "11111111-1111-4111-8111-111111111111";
    const enc = encodeRunListCursor(42, runId);
    const dec = decodeRunListCursor(enc);
    expect(dec.seq).toBe(42);
    expect(dec.runId).toBe(runId);
  });

  it("parses filters from search", () => {
    const f = filtersFromSearch("?status=running&workflow_profile=micro_slice&limit=10");
    expect(f.status).toBe("running");
    expect(f.workflow_profile).toBe("micro_slice");
    expect(f.limit).toBe(10);
  });

  it("builds runs query with cursor", () => {
    const q = buildRunsQuery({
      limit: 25,
      status: "",
      workflow_profile: "",
      cursor: "abc",
    });
    expect(q).toContain("cursor=abc");
    expect(q).toContain("include_summary=1");
  });
});
