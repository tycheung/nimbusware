import { describe, expect, it } from "vitest";
import { fmtFit, fmtRate, formatGateSummary } from "../js/formatters.js";
import { parseApiErrorBody } from "../js/api-core.js";
import { mapHttp503PeelMiss } from "../js/peel-http.js";
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

describe("mapHttp503PeelMiss (sak493-f / sak495-e)", () => {
  it("maps broker_compute_only 503 to compute peel miss", () => {
    const text = JSON.stringify({
      detail: {
        code: "broker_compute_only",
        message: "compute unavailable under COMPUTE=2",
      },
    });
    const miss = mapHttp503PeelMiss(503, text);
    expect(miss).not.toBeNull();
    expect(miss.via).toBe("broker_miss");
    expect(miss.error).toBe("compute unavailable under COMPUTE=2");
    expect(miss.nodes).toEqual([]);
  });

  it("maps broker_capacity_only 503 to capacity peel miss", () => {
    const text = JSON.stringify({
      detail: {
        code: "broker_capacity_only",
        message: "capacity unavailable under CAPACITY=2",
      },
    });
    const miss = mapHttp503PeelMiss(503, text);
    expect(miss).not.toBeNull();
    expect(miss.capacity_source).toBe("broker_miss");
    expect(miss.error).toBe("capacity unavailable under CAPACITY=2");
  });

  it("maps broker_memory_only 503 to memory peel miss", () => {
    const text = JSON.stringify({
      detail: {
        code: "broker_memory_only",
        message: "memory unavailable under MEMORY=2",
      },
    });
    const miss = mapHttp503PeelMiss(503, text);
    expect(miss).not.toBeNull();
    expect(miss.via).toBe("broker_miss");
    expect(miss.status).toBe("degraded");
    expect(miss.feature).toBe("fleet_memory_search");
    expect(miss.error).toBe("memory unavailable under MEMORY=2");
    expect(miss.hits).toEqual([]);
    expect(miss.hit_count).toBe(0);
  });

  it("maps broker_llm_unavailable 503 to LLM peel miss", () => {
    const text = JSON.stringify({
      detail: {
        code: "broker_llm_unavailable",
        message: "LLM unavailable under LLM=2",
      },
    });
    const miss = mapHttp503PeelMiss(503, text);
    expect(miss).not.toBeNull();
    expect(miss.via).toBe("broker_miss");
    expect(miss.status).toBe("degraded");
    expect(miss.feature).toBe("llm");
    expect(miss.error).toBe("LLM unavailable under LLM=2");
  });

  it("returns null for non-503 or unknown problem codes", () => {
    expect(mapHttp503PeelMiss(502, '{"detail":{"code":"broker_compute_only"}}')).toBeNull();
    expect(mapHttp503PeelMiss(503, '{"detail":{"code":"other"}}')).toBeNull();
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
