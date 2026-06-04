import { describe, expect, it, beforeEach } from "vitest";

beforeEach(() => {
  global.window = {
    __NIMBUSWARE__: { api_base: "/v1/test" },
    dispatchEvent: () => {},
  };
});

describe("api-client bootstrap", () => {
  it("reads api_base from window", async () => {
    const { apiBase } = await import("../static/js/api-client.js");
    expect(apiBase()).toBe("/v1/test");
  });
});

describe("sse-client parse", () => {
  it("parseSseJson handles valid JSON", async () => {
    const { parseSseJson } = await import("../static/js/sse-client.js");
    const body = parseSseJson({ data: '{"ok":true}' });
    expect(body.ok).toBe(true);
  });
});
