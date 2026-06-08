import { describe, expect, it, beforeEach, vi } from "vitest";

const storage = new Map();

beforeEach(() => {
  storage.clear();
  global.sessionStorage = {
    getItem: (k) => storage.get(k) ?? null,
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
  };
  global.window = {
    location: { search: "", hash: "#/progress" },
    dispatchEvent: () => {},
  };
  global.document = {
    getElementById: () => null,
  };
});

describe("session-hub", () => {
  it("persists and resolves run_id per project", async () => {
    const hub = await import("../static/js/session-hub.js");
    hub.setActiveProjectId("proj-1");
    hub.setActiveRun("proj-1", "run-aaa");
    expect(hub.getStoredRunId("proj-1")).toBe("run-aaa");
    expect(hub.resolveRunId()).toBe("run-aaa");
  });

  it("prefers URL run_id over session storage", async () => {
    const hub = await import("../static/js/session-hub.js");
    hub.setActiveProjectId("proj-1");
    hub.setActiveRun("proj-1", "run-stored");
    window.location.search = "?run_id=run-from-url";
    expect(hub.resolveRunId()).toBe("run-from-url");
  });

  it("fetchActiveRunForProject matches project in run summaries", async () => {
    const hub = await import("../static/js/session-hub.js");
    const apiJson = vi.fn(async () => ({
      run_ids: ["r1", "r2"],
      summaries: {
        r1: { run_created_metadata: { project: { id: "proj-x" } } },
        r2: { run_created_metadata: { project: { id: "proj-y" } } },
      },
    }));
    const rid = await hub.fetchActiveRunForProject("proj-y", apiJson);
    expect(rid).toBe("r2");
    expect(apiJson).toHaveBeenCalledWith("/runs?status=running&include_summary=1&limit=50");
  });
});
