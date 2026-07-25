/** Shared HTTP 503 → peel miss mapping (`sak493-f` / `sak495-e`). */

const BROKER_COMPUTE_ONLY = "broker_compute_only";
const BROKER_CAPACITY_ONLY = "broker_capacity_only";
const BROKER_MEMORY_ONLY = "broker_memory_only";
const BROKER_SANDBOX_ONLY = "broker_sandbox_only";
const BROKER_TOOLS_ONLY = "broker_tools_only";
const BROKER_RESEARCH_ONLY = "broker_research_only";
const BROKER_EGRESS_ONLY = "broker_egress_only";
const BROKER_LLM_UNAVAILABLE = "broker_llm_unavailable";

const BROKER_PROBLEM_CODES = new Set([
  BROKER_COMPUTE_ONLY,
  BROKER_CAPACITY_ONLY,
  BROKER_MEMORY_ONLY,
  BROKER_SANDBOX_ONLY,
  BROKER_TOOLS_ONLY,
  BROKER_RESEARCH_ONLY,
  BROKER_EGRESS_ONLY,
  BROKER_LLM_UNAVAILABLE,
]);

/** Parse FastAPI 503 problem ``detail``. */
export function parseBrokerProblemDetail(detail) {
  if (!detail || typeof detail !== "object") return null;
  const code = detail.code;
  if (typeof code !== "string" || !BROKER_PROBLEM_CODES.has(code)) {
    return null;
  }
  const message = detail.message;
  return {
    code: String(code),
    message: typeof message === "string" && message.length > 0 ? message : String(code),
  };
}

/** Map broker-only HTTP 503 problem to structured peel miss. */
export function mapBrokerProblemToPeelMiss(detail, feature) {
  const error = detail.message || detail.code;
  if (detail.code === BROKER_CAPACITY_ONLY) {
    return {
      via: "broker_miss",
      capacity_source: "broker_miss",
      fit_via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "platform_hardware",
    };
  }
  if (detail.code === BROKER_MEMORY_ONLY) {
    return {
      via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "fleet_memory_search",
      hits: [],
      hit_count: 0,
    };
  }
  if (detail.code === BROKER_LLM_UNAVAILABLE) {
    return {
      via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "llm",
    };
  }
  if (detail.code === BROKER_SANDBOX_ONLY) {
    return {
      via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "sandbox_exec",
    };
  }
  if (detail.code === BROKER_TOOLS_ONLY) {
    return {
      via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "shell",
    };
  }
  if (detail.code === BROKER_RESEARCH_ONLY) {
    return {
      via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "research_fetch",
    };
  }
  if (detail.code === BROKER_EGRESS_ONLY) {
    return {
      via: "broker_miss",
      status: "degraded",
      error,
      feature: feature || "egress",
    };
  }
  return {
    via: "broker_miss",
    status: "degraded",
    error,
    feature: feature || "compute",
    nodes: [],
  };
}

/** Map HTTP 503 response text carrying broker-only problem bodies. */
export function mapHttp503PeelMiss(status, text, feature) {
  if (status !== 503) return null;
  try {
    const prob = JSON.parse(text);
    const parsed = parseBrokerProblemDetail(prob.detail ?? prob);
    if (!parsed) return null;
    return mapBrokerProblemToPeelMiss(parsed, feature);
  } catch {
    return null;
  }
}

/** Peel miss from fetch throw (503 problem in message). */
export function peelMissFromFetchError(e) {
  const status = e?.status;
  const msg = String(e?.message || e);
  if (status === 503) {
    const body = msg.replace(/^503:\s*/, "");
    const mapped = mapHttp503PeelMiss(
      503,
      body.startsWith("{") ? body : JSON.stringify({ detail: body }),
    );
    if (mapped) return mapped;
  }
  const jsonMatch = /^503:\s*(\{[\s\S]*\})/.exec(msg);
  if (jsonMatch) {
    return mapHttp503PeelMiss(503, jsonMatch[1]);
  }
  return null;
}
