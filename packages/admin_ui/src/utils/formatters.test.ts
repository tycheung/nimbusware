import { describe, expect, it } from "vitest";
import { fmtFit, fmtRate } from "./formatters";
import { parseApiErrorBody } from "./parseApiError";

describe("formatters", () => {
  it("fmtRate formats fractions as percentages", () => {
    expect(fmtRate(0.825)).toBe("82.5%");
    expect(fmtRate(null)).toBe("—");
  });

  it("fmtFit formats numbers with two decimals", () => {
    expect(fmtFit(0.826)).toBe("0.83");
    expect(fmtFit(undefined)).toBe("—");
  });
});

describe("parseApiErrorBody", () => {
  it("extracts detail from problem JSON", () => {
    expect(parseApiErrorBody('{"detail":"not found"}')).toBe("not found");
    expect(parseApiErrorBody('{"title":"Forbidden"}')).toBe("Forbidden");
  });

  it("returns plain text when not JSON", () => {
    expect(parseApiErrorBody("upstream error")).toBe("upstream error");
  });
});
