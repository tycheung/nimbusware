import { describe, expect, it } from "vitest";
import {
  formatReadCatchMessage,
  isCapacityMiss,
  isComputeMiss,
  isDomainPeelMiss,
  isEgressMiss,
  isLlmMiss,
  isMemoryMiss,
  isReadPeelMiss,
  isResearchMiss,
  isSandboxMiss,
  isToolsMiss,
  mapHttp503PeelMiss,
  parseBrokerProblemDetail,
  parseSseJson,
  parseSsePeelMiss,
  peelMissFromFetchError,
  writeMissMessage,
} from "./peel_assert";

describe("mapHttp503PeelMiss (sak492-i)", () => {
  it("maps broker_compute_only 503 to compute peel miss", () => {
    const text = JSON.stringify({
      detail: {
        code: "broker_compute_only",
        message: "compute unavailable under COMPUTE=2",
      },
    });
    const miss = mapHttp503PeelMiss(503, text);
    expect(miss).not.toBeNull();
    expect(isComputeMiss(miss)).toBe(true);
    expect(miss?.via).toBe("broker_miss");
    expect(miss?.error).toBe("compute unavailable under COMPUTE=2");
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
    expect(isCapacityMiss(miss)).toBe(true);
    expect(miss?.capacity_source).toBe("broker_miss");
    expect(miss?.error).toBe("capacity unavailable under CAPACITY=2");
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
    expect(isMemoryMiss(miss)).toBe(true);
    expect(miss?.via).toBe("broker_miss");
    expect(miss?.error).toBe("memory unavailable under MEMORY=2");
  });

  it("returns null for non-503 or unknown problem codes", () => {
    expect(mapHttp503PeelMiss(502, '{"detail":{"code":"broker_compute_only"}}')).toBeNull();
    expect(mapHttp503PeelMiss(503, '{"detail":{"code":"other"}}')).toBeNull();
  });

  it("detects raw problem detail codes on miss detectors", () => {
    expect(
      isComputeMiss({ code: "broker_compute_only", message: "down" }),
    ).toBe(true);
    expect(
      isCapacityMiss({ code: "broker_capacity_only", message: "down" }),
    ).toBe(true);
    expect(
      isMemoryMiss({ code: "broker_memory_only", message: "down" }),
    ).toBe(true);
    expect(parseBrokerProblemDetail({ code: "broker_compute_only", message: "x" })?.code).toBe(
      "broker_compute_only",
    );
  });
});

describe("isReadPeelMiss (sak495-f)", () => {
  it("detects broker_miss bodies without treating bare error as miss", () => {
    expect(isReadPeelMiss({ via: "broker_miss", error: "down" })).toBe(true);
    expect(isReadPeelMiss({ status: "degraded", error: "down" })).toBe(true);
    expect(isReadPeelMiss({ code: "broker_compute_only", message: "down" })).toBe(true);
    expect(isReadPeelMiss({ error: "validation failed" })).toBe(false);
    expect(isComputeMiss({ error: "validation failed" })).toBe(false);
  });
});

describe("peelMissFromFetchError / formatReadCatchMessage (sak493-g / sak494-h)", () => {
  it("peels compute 503 from thrown fetch error", () => {
    const body = JSON.stringify({
      detail: { code: "broker_compute_only", message: "compute down" },
    });
    const err = new Error(`503: ${body}`) as Error & { status?: number };
    err.status = 503;
    const miss = peelMissFromFetchError(err);
    expect(miss).not.toBeNull();
    expect(isComputeMiss(miss)).toBe(true);
    expect(formatReadCatchMessage(err, "fallback")).toBe("compute down");
  });

  it("peels capacity 503 from thrown fetch error", () => {
    const body = JSON.stringify({
      detail: { code: "broker_capacity_only", message: "capacity down" },
    });
    const err = new Error(`503: ${body}`) as Error & { status?: number };
    err.status = 503;
    const miss = peelMissFromFetchError(err);
    expect(miss).not.toBeNull();
    expect(isCapacityMiss(miss)).toBe(true);
    expect(formatReadCatchMessage(err, "fallback")).toContain("Capacity peel miss");
  });

  it("peels memory 503 from thrown fetch error", () => {
    const body = JSON.stringify({
      detail: { code: "broker_memory_only", message: "memory down" },
    });
    const err = new Error(`503: ${body}`) as Error & { status?: number };
    err.status = 503;
    const miss = peelMissFromFetchError(err);
    expect(miss).not.toBeNull();
    expect(isMemoryMiss(miss)).toBe(true);
    expect(formatReadCatchMessage(err, "fallback")).toBe("memory down");
  });

  it("formatReadCatchMessage falls back for non-peel errors", () => {
    expect(formatReadCatchMessage(new Error("network down"), "runs unavailable")).toBe(
      "network down",
    );
  });

  it("peels LLM/sandbox/research/egress/tools 503 from thrown fetch error (sak497-f)", () => {
    const cases = [
      ["broker_llm_unavailable", "llm down", isLlmMiss],
      ["broker_sandbox_only", "sandbox down", isSandboxMiss],
      ["broker_tools_only", "tools down", isToolsMiss],
      ["broker_research_only", "research down", isResearchMiss],
      ["broker_egress_only", "egress down", isEgressMiss],
    ] as const;
    for (const [code, message, detector] of cases) {
      const body = JSON.stringify({ detail: { code, message } });
      const err = new Error(`503: ${body}`) as Error & { status?: number };
      err.status = 503;
      const miss = peelMissFromFetchError(err);
      expect(miss).not.toBeNull();
      expect(detector(miss)).toBe(true);
      expect(formatReadCatchMessage(err, "fallback")).toBe(message);
    }
  });
});

describe("parseSsePeelMiss (sak491-i)", () => {
  it("returns null for non-miss payloads", () => {
    expect(parseSsePeelMiss({ data: '{"headline":"ok"}' })).toBeNull();
  });

  it("returns miss body for broker_miss via", () => {
    const miss = parseSsePeelMiss({
      data: JSON.stringify({
        via: "broker_miss",
        feature: "theater_stream",
        error: "down",
        status: "degraded",
      }),
    });
    expect(miss).not.toBeNull();
    expect(isComputeMiss(miss)).toBe(true);
    expect(miss?.feature).toBe("theater_stream");
  });

  it("parseSseJson returns null on bad JSON", () => {
    expect(parseSseJson({ data: "not-json" })).toBeNull();
  });

  it("returns domain peel miss bodies by problem code (sak497-f)", () => {
    const cases = [
      ["broker_llm_unavailable", "llm down", isLlmMiss],
      ["broker_sandbox_only", "sandbox down", isSandboxMiss],
      ["broker_research_only", "research down", isResearchMiss],
    ] as const;
    for (const [code, message, detector] of cases) {
      const miss = parseSsePeelMiss({
        data: JSON.stringify({ code, error: message }),
      });
      expect(miss).not.toBeNull();
      expect(detector(miss)).toBe(true);
      expect(miss?.error).toBe(message);
    }
  });
});

describe("isDomainPeelMiss admin read paths (sak499-d)", () => {
  it("replaces isComputeMiss / isReadPeelMiss / isMemoryMiss for page guards", () => {
    expect(isDomainPeelMiss({ via: "broker_miss", error: "down" })).toBe(true);
    expect(isDomainPeelMiss({ status: "degraded", error: "down" })).toBe(true);
    expect(isDomainPeelMiss({ code: "broker_compute_only", message: "down" })).toBe(true);
    expect(isDomainPeelMiss({ code: "broker_memory_only", error: "memory down" })).toBe(true);
    expect(isDomainPeelMiss({ code: "broker_llm_unavailable", error: "llm down" })).toBe(true);
    expect(isDomainPeelMiss({ error: "validation failed" })).toBe(false);
    expect(isReadPeelMiss({ error: "validation failed" })).toBe(false);
    expect(isComputeMiss({ error: "validation failed" })).toBe(false);
  });

  it("formatReadCatchMessage handles domain peel throws", () => {
    const body = JSON.stringify({
      detail: { code: "broker_memory_only", message: "memory down" },
    });
    const err = new Error(`503: ${body}`) as Error & { status?: number };
    err.status = 503;
    expect(isDomainPeelMiss(peelMissFromFetchError(err))).toBe(true);
    expect(formatReadCatchMessage(err, "fallback")).toBe("memory down");
  });
});

describe("isDomainPeelMiss fleet mesh panel (sak500-c)", () => {
  it("detects session_compute mesh peel miss bodies for panel guards", () => {
    expect(
      isDomainPeelMiss({
        via: "broker_miss",
        status: "degraded",
        error: "compute nodes unavailable",
        feature: "session_compute",
      }),
    ).toBe(true);
    expect(
      isDomainPeelMiss({
        code: "broker_compute_only",
        message: "compute down",
        feature: "session_compute",
      }),
    ).toBe(true);
    expect(
      isDomainPeelMiss({
        error: "validation failed",
        feature: "session_compute",
      }),
    ).toBe(false);
  });
});

describe("writeMissMessage (sak497-f)", () => {
  it("formats domain peel miss bodies on write path", () => {
    expect(
      writeMissMessage({ code: "broker_research_only", error: "research down" }, "fallback"),
    ).toBe("research down");
    expect(
      writeMissMessage({ code: "broker_llm_unavailable", error: "llm down" }, "fallback"),
    ).toBe("llm down");
    expect(writeMissMessage({ stdout: "ok", via: "broker" }, "fallback")).toBeNull();
  });
});
