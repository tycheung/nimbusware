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

  it("parseSseJson returns null on invalid JSON", async () => {
    const { parseSseJson } = await import("../static/js/sse-client.js");
    expect(parseSseJson({ data: "not-json" })).toBeNull();
  });
});

describe("sse-client theaterLineText", () => {
  it("prefers legacy message field", async () => {
    const { theaterLineText } = await import("../static/js/sse-client.js");
    expect(theaterLineText({ message: "  hello  " })).toBe("hello");
  });

  it("formats headline and body_md from API theater payloads", async () => {
    const { theaterLineText } = await import("../static/js/sse-client.js");
    expect(
      theaterLineText({ headline: "Planner", body_md: "Reviewing scope" }),
    ).toBe("Planner — Reviewing scope");
    expect(theaterLineText({ headline: "Done" })).toBe("Done");
  });

  it("joins nested messages array", async () => {
    const { theaterLineText } = await import("../static/js/sse-client.js");
    expect(
      theaterLineText({
        messages: [{ headline: "A" }, { message: "B" }],
      }),
    ).toBe("A · B");
  });
});
