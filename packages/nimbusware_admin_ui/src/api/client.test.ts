import { describe, expect, it } from "vitest";
import { apiBase } from "./client";

describe("apiBase", () => {
  it("returns bootstrap api_base", () => {
    expect(typeof apiBase()).toBe("string");
  });
});
