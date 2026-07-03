import { describe, expect, it } from "vitest";
import { fmtFit, fmtRate, formatGateSummary } from "../js/formatters.js";
import { parseApiErrorBody } from "../js/api-core.js";
import { scorecardFromTimeline } from "../js/launch-scorecard.js";

describe("formatters", () => {
  it("fmtRate formats fractions", () => {
    expect(fmtRate(0.5)).toBe("50.0%");
    expect(fmtRate(null)).toBe("—");
  });

  it("formatGateSummary joins objects", () => {
    expect(formatGateSummary({ passed: 2, failed: 1 })).toContain("passed: 2");
  });
});

describe("api-core", () => {
  it("parseApiErrorBody extracts detail", () => {
    expect(parseApiErrorBody('{"detail":"missing"}')).toBe("missing");
  });
});

describe("launch-scorecard", () => {
  it("reads latest launch_eval.completed", () => {
    const card = scorecardFromTimeline({
      events: [
        {
          event_type: "stage.passed",
          payload: { stage_name: "launch_eval.completed" },
          metadata: { aggregate: 0.9, passed: true },
        },
      ],
    });
    expect(card?.aggregate).toBe(0.9);
    expect(card?.passed).toBe(true);
  });
});
