/** Shared peel assert helpers for admin UI (`sak447-h` / `sak448-f` / `sak449-g/h` / `sak491-i` / `sak492-i` / `sak493-i` / `sak496-h` / `sak496-i` / `sak497-f` / `sak497-j`). */

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

type BrokerProblemDetail = {
  code: string;
  message: string;
};

/** Parse FastAPI 503 problem ``detail`` (`sak492-i`). */
export function parseBrokerProblemDetail(detail: unknown): BrokerProblemDetail | null {
  if (!detail || typeof detail !== "object") return null;
  const code = (detail as { code?: unknown }).code;
  if (typeof code !== "string" || !BROKER_PROBLEM_CODES.has(code)) return null;
  const message = (detail as { message?: unknown }).message;
  return {
    code: String(code),
    message: typeof message === "string" && message.length > 0 ? message : String(code),
  };
}

/** Map broker-only HTTP 503 problem to structured peel miss (`sak492-i`). */
export function mapBrokerProblemToPeelMiss(
  detail: BrokerProblemDetail,
  feature?: string,
): Record<string, unknown> {
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

/** Map HTTP 503 response text carrying broker-only problem bodies (`sak492-i`). */
export function mapHttp503PeelMiss(
  status: number,
  text: string,
): Record<string, unknown> | null {
  if (status !== 503) return null;
  try {
    const prob = JSON.parse(text) as { detail?: unknown };
    const parsed = parseBrokerProblemDetail(prob.detail ?? prob);
    if (!parsed) return null;
    return mapBrokerProblemToPeelMiss(parsed);
  } catch {
    return null;
  }
}

/** Fallback: peel miss from fetch throw (503 problem in message) (`sak492-i`). */
export function peelMissFromFetchError(e: unknown): Record<string, unknown> | null {
  const err = e as Error & { status?: number };
  const status = err?.status;
  const msg = String(err?.message || e);
  if (status === 503) {
    const body = msg.replace(/^503:\s*/, "");
    const mapped = mapHttp503PeelMiss(503, body.startsWith("{") ? body : JSON.stringify({ detail: body }));
    if (mapped) return mapped;
  }
  const jsonMatch = /^503:\s*(\{[\s\S]*\})/.exec(msg);
  if (jsonMatch) {
    return mapHttp503PeelMiss(503, jsonMatch[1]);
  }
  return null;
}

/** Fleet/hardware status: pass through miss bodies; throw on hard error without nodes. */
export function normalizeStatusMiss<
  T extends { nodes?: unknown; via?: string; status?: string; error?: string },
>(raw: T): T {
  if (raw.via === "broker_miss" || raw.status === "degraded") {
    return {
      ...raw,
      nodes: Array.isArray(raw.nodes) ? raw.nodes : [],
    };
  }
  if (raw.error != null && String(raw.error).length > 0) {
    throw new Error(`broker_miss: ${String(raw.error)}`);
  }
  if (!Array.isArray(raw.nodes)) {
    throw new Error("broker_miss: missing or non-list key nodes");
  }
  return raw;
}

/** Shared capacity peel miss detector for Hardware/Fleet pages (`sak448-g`). */
export function isCapacityMiss(body: {
  capacity_source?: unknown;
  via?: unknown;
  fit_via?: unknown;
  status?: unknown;
  error?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  if (!body || typeof body !== "object") return false;
  if (body.code === BROKER_CAPACITY_ONLY) return true;
  const src = body.capacity_source;
  const via = body.via;
  const fit = body.fit_via;
  if (src === "broker_miss" || via === "broker_miss" || fit === "broker_miss") {
    return true;
  }
  if (typeof src === "string" && src.toLowerCase().includes("broker_miss")) {
    return true;
  }
  if (typeof fit === "string" && fit.toLowerCase().includes("broker_miss")) {
    return true;
  }
  if (body.status === "degraded") return true;
  if (typeof body.error === "string" && body.error.length > 0) return true;
  return false;
}

/** Read-path peel miss (OAuth/analytics — not compute-specific) (`sak495-f`). */
export function isReadPeelMiss(body: {
  via?: unknown;
  status?: unknown;
  capacity_source?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  if (!body || typeof body !== "object") return false;
  if (body.via === "broker_miss" || body.capacity_source === "broker_miss") return true;
  if (body.status === "degraded") return true;
  if (
    body.code === BROKER_COMPUTE_ONLY ||
    body.code === BROKER_CAPACITY_ONLY ||
    body.code === BROKER_MEMORY_ONLY ||
    body.code === BROKER_SANDBOX_ONLY ||
    body.code === BROKER_TOOLS_ONLY ||
    body.code === BROKER_RESEARCH_ONLY ||
    body.code === BROKER_EGRESS_ONLY ||
    body.code === BROKER_LLM_UNAVAILABLE
  ) {
    return true;
  }
  return false;
}

/** Compute/session miss detector (`sak449-g` / `sak496-h`). */
export function isComputeMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  if (!body || typeof body !== "object") return false;
  if (body.code === BROKER_COMPUTE_ONLY) return true;
  if (body.via === "broker_miss" || body.status === "degraded") return true;
  return false;
}

function featureDomainMiss(
  body: {
    via?: unknown;
    status?: unknown;
    error?: unknown;
    feature?: unknown;
    code?: unknown;
  } | null | undefined,
  domainCode: string,
  keywords: string[],
): boolean {
  if (!body || typeof body !== "object") return false;
  if (body.code === domainCode) return true;
  if (isComputeMiss(body)) return true;
  const feat = body.feature;
  if (typeof feat === "string") {
    const low = feat.toLowerCase();
    if (keywords.some((kw) => low.includes(kw))) {
      return body.via === "broker_miss" || (body.error != null && String(body.error).length > 0);
    }
  }
  return false;
}

/** Sandbox peel miss detector (`sak496-i`). */
export function isSandboxMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return featureDomainMiss(body, BROKER_SANDBOX_ONLY, ["sandbox"]);
}

/** Tools peel miss detector (`sak496-i`). */
export function isToolsMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return featureDomainMiss(body, BROKER_TOOLS_ONLY, ["tools", "shell"]);
}

/** Research peel miss detector (`sak496-i`). */
export function isResearchMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return featureDomainMiss(body, BROKER_RESEARCH_ONLY, ["research"]);
}

/** Egress peel miss detector (`sak496-i`). */
export function isEgressMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return featureDomainMiss(body, BROKER_EGRESS_ONLY, ["egress"]);
}

/** LLM peel miss detector (`sak496-i`). */
export function isLlmMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return featureDomainMiss(body, BROKER_LLM_UNAVAILABLE, ["llm"]);
}

/** Non-capacity peel miss across compute + domain offers (`sak497-f` / `sak499-d`). */
export function isDomainPeelMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return (
    isComputeMiss(body) ||
    isMemoryMiss(body) ||
    isLlmMiss(body) ||
    isSandboxMiss(body) ||
    isToolsMiss(body) ||
    isResearchMiss(body) ||
    isEgressMiss(body)
  );
}

/** Fleet memory / search miss detector (`sak480-g` / `sak493-i`). */
export function isMemoryMiss(body: {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  feature?: unknown;
  code?: unknown;
} | null | undefined): boolean {
  return featureDomainMiss(body, BROKER_MEMORY_ONLY, ["memory"]);
}

/** Domain peel miss banner (`sak497-j`). */
export function formatDomainMissMessage(
  body: {
    error?: unknown;
    via?: unknown;
    feature?: unknown;
  } | null | undefined,
  fallback = "broker_miss",
): string {
  return formatPeelMissMessage(body, fallback);
}

/** Format peel miss banner text (`sak480-g` / `sak480-h`). */
export function formatPeelMissMessage(
  body: {
    error?: unknown;
    via?: unknown;
    capacity_source?: unknown;
    fit_via?: unknown;
    feature?: unknown;
  } | null | undefined,
  fallback = "broker_miss",
): string {
  if (!body || typeof body !== "object") return fallback;
  const err = body.error != null ? String(body.error) : "";
  if (err) return err;
  const src = body.capacity_source != null ? String(body.capacity_source) : "";
  if (src) return src;
  const via = body.via != null ? String(body.via) : "";
  if (via) return via;
  const feat = body.feature != null ? String(body.feature) : "";
  if (feat) return feat;
  return fallback;
}

/** Capacity-specific miss banner (`sak480-h`). */
export function formatCapacityMissMessage(
  body: {
    error?: unknown;
    via?: unknown;
    capacity_source?: unknown;
    fit_via?: unknown;
    feature?: unknown;
  } | null | undefined,
): string {
  const base = formatPeelMissMessage(body, "broker_miss");
  const src = body?.capacity_source != null ? String(body.capacity_source) : "—";
  const fit = body?.fit_via != null ? String(body.fit_via) : "—";
  if (body?.capacity_source != null || body?.fit_via != null) {
    return `Capacity peel miss: capacity_source=${src} · fit_via=${fit} (feature=${String(body?.feature || "platform_hardware")} · status=degraded)`;
  }
  return `Capacity peel miss: ${base}`;
}

/**
 * Pass through peel miss bodies for compute actions; otherwise null (caller asserts).
 * (`sak449-h`)
 */
export function normalizeComputeActionMiss<T extends Record<string, unknown>>(
  raw: T,
): T | null {
  if (isComputeMiss(raw)) {
    return raw;
  }
  return null;
}

type PeelWriteBody = {
  via?: unknown;
  status?: unknown;
  error?: unknown;
  capacity_source?: unknown;
  fit_via?: unknown;
  feature?: unknown;
  code?: unknown;
};

function isExplicitCapacityMiss(
  body: { code?: unknown; capacity_source?: unknown; fit_via?: unknown } | null | undefined,
): boolean {
  if (!body || typeof body !== "object") return false;
  return (
    body.code === BROKER_CAPACITY_ONLY ||
    body.capacity_source != null ||
    body.fit_via != null
  );
}

/** Write-path peel miss message; null when response is OK (`sak486-h` / `sak488-h` / `sak497-f`). */
export function writeMissMessage(
  body: PeelWriteBody | null | undefined,
  fallback: string,
): string | null {
  if (isExplicitCapacityMiss(body) && isCapacityMiss(body)) {
    return formatCapacityMissMessage(body);
  }
  if (isDomainPeelMiss(body)) {
    return formatDomainMissMessage(body, fallback);
  }
  if (isCapacityMiss(body)) {
    return formatCapacityMissMessage(body);
  }
  return null;
}

/** Throw when write response is a peel miss (`sak486-h`). */
export function assertWriteOk<T extends PeelWriteBody>(
  body: T | null | undefined,
  fallback: string,
): T {
  const miss = writeMissMessage(body, fallback);
  if (miss) throw new Error(miss);
  return body as T;
}

/** Catch-path formatter for admin write actions (`sak486-h`). */
export function formatWriteCatchMessage(e: unknown, fallback: string): string {
  return formatPeelMissMessage({ error: String((e as Error).message || e) }, fallback);
}

/** Read-path catch formatter: peel 503 problem throws before generic error (`sak493-g` / `sak494-h` / `sak497-f`). */
export function formatReadCatchMessage(e: unknown, fallback: string): string {
  const miss = peelMissFromFetchError(e);
  if (miss) {
    if (miss.capacity_source != null) return formatCapacityMissMessage(miss);
    if (isReadPeelMiss(miss) || isDomainPeelMiss(miss)) {
      return formatDomainMissMessage(miss, fallback);
    }
  }
  return formatPeelMissMessage({ error: String((e as Error).message || e) }, fallback);
}

export function assertBrokerComputeRecordOk(
  raw: Record<string, unknown> | null | undefined,
  recordKey: "node" | "work" = "work",
): Record<string, unknown> {
  if (!raw || typeof raw !== "object") {
    throw new Error(`broker_miss: non-object response for ${recordKey}`);
  }
  if ("error" in raw && raw.error != null) {
    throw new Error(`broker_miss: ${String(raw.error)}`);
  }
  const rec = raw[recordKey];
  if (rec && typeof rec === "object") {
    return raw;
  }
  if (recordKey === "work" && raw.id != null) {
    return raw;
  }
  if (recordKey === "node" && (raw.id != null || raw.node_id != null) && !("nodes" in raw)) {
    return raw;
  }
  throw new Error(`broker_miss: missing ${recordKey} record`);
}

/** Empty queue → work null + via=broker; hard miss throws. */
export function normalizeClaimWorkResponse(
  raw: Record<string, unknown> | null | undefined,
): Record<string, unknown> {
  if (!raw || typeof raw !== "object") {
    throw new Error("broker_miss: claim: non-object response");
  }
  const work = raw.work;
  const err = raw.error;
  const errStr = err == null ? "" : String(err);
  const emptyPoll =
    work == null &&
    (!("error" in raw) ||
      err == null ||
      errStr.toLowerCase().includes("empty") ||
      errStr.toLowerCase().includes("no work"));
  if (emptyPoll) {
    return { work: null, via: "broker" };
  }
  return assertBrokerComputeRecordOk(raw, "work");
}

/** Parse SSE frame JSON; null on malformed payloads (`sak491-i`). */
export function parseSseJson(ev: { data?: string }): Record<string, unknown> | null {
  try {
    return JSON.parse(ev.data || "") as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** Peel miss body from SSE ``event: error`` (or any frame carrying broker_miss) (`sak491-i` / `sak497-f`). */
export function parseSsePeelMiss(ev: { data?: string }): Record<string, unknown> | null {
  const data = parseSseJson(ev);
  if (!data) return null;
  if (isExplicitCapacityMiss(data) && isCapacityMiss(data)) return data;
  if (isDomainPeelMiss(data)) return data;
  if (isCapacityMiss(data)) return data;
  return null;
}

/** List responses — error or non-list key is a peel miss. */
export function assertBrokerComputeListOk(
  raw: Record<string, unknown> | null | undefined,
  listKey: "nodes" | "work" = "nodes",
): Record<string, unknown> {
  if (!raw || typeof raw !== "object") {
    throw new Error(`broker_miss: non-object response for ${listKey}`);
  }
  if ("error" in raw && raw.error != null) {
    throw new Error(`broker_miss: ${String(raw.error)}`);
  }
  if (!Array.isArray(raw[listKey])) {
    throw new Error(`broker_miss: missing or non-list key ${listKey}`);
  }
  return raw;
}
