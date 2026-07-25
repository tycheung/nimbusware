import { parseApiErrorBody } from "@nimbusware/ui-shared/js/api-core.js";
import {
  assertBrokerComputeListOk,
  assertBrokerComputeRecordOk,
  assertWriteOk,
  formatCapacityMissMessage,
  formatPeelMissMessage,
  formatReadCatchMessage,
  formatWriteCatchMessage,
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
  normalizeClaimWorkResponse,
  normalizeComputeActionMiss,
  normalizeStatusMiss,
  parseSseJson,
  parseSsePeelMiss,
  peelMissFromFetchError,
  writeMissMessage,
} from "./peel_assert";
import { openSseStream } from "./sse_client";

export {
  assertBrokerComputeListOk,
  assertBrokerComputeRecordOk,
  assertWriteOk,
  formatCapacityMissMessage,
  formatPeelMissMessage,
  formatReadCatchMessage,
  formatWriteCatchMessage,
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
  normalizeClaimWorkResponse,
  normalizeComputeActionMiss,
  normalizeStatusMiss,
  parseSseJson,
  parseSsePeelMiss,
  peelMissFromFetchError,
  writeMissMessage,
} from "./peel_assert";
export { openSseStream } from "./sse_client";
export type { OpenSseStreamOptions, SseStreamHandle } from "./sse_client";

export type Bootstrap = {
  api_base: string;
  edition: string;
  quick_mode?: boolean;
  admin_token_required?: boolean;
  features?: {
    enterprise_fleet_ui?: boolean;
    oidc_login_ready?: boolean;
  };
};

export const ENTERPRISE_API_KEY_KEY = "nimbusware_enterprise_api_key";
export const ENTERPRISE_TENANT_SLUG_KEY = "nimbusware_enterprise_tenant_slug";
export const ENTERPRISE_TENANT_KEYS_KEY = "nimbusware_enterprise_tenant_keys";

let bootstrap: Bootstrap = { api_base: "/v1", edition: "individual" };

export async function loadBootstrap(): Promise<Bootstrap> {
  const res = await fetch("/v1/admin/app/bootstrap.json");
  if (res.ok) {
    bootstrap = await res.json();
  }
  return bootstrap;
}

export function apiBase(): string {
  return bootstrap.api_base.replace(/\/$/, "");
}

export function adminHeaders(): Record<string, string> {
  const token = sessionStorage.getItem("nimbusware_admin_token");
  return token ? { "X-Nimbusware-Admin-Token": token } : {};
}

export function enterpriseApiKey(): string {
  return (sessionStorage.getItem(ENTERPRISE_API_KEY_KEY) || "").trim();
}

export function enterpriseApiHeaders(): Record<string, string> {
  const key = enterpriseApiKey();
  return key ? { "X-Nimbusware-Api-Key": key } : {};
}

export function setEnterpriseApiKey(value: string): void {
  const trimmed = value.trim();
  if (trimmed) {
    sessionStorage.setItem(ENTERPRISE_API_KEY_KEY, trimmed);
  } else {
    sessionStorage.removeItem(ENTERPRISE_API_KEY_KEY);
  }
}

export function selectedEnterpriseTenantSlug(): string {
  return (sessionStorage.getItem(ENTERPRISE_TENANT_SLUG_KEY) || "").trim();
}

export function setEnterpriseTenantSlug(slug: string): void {
  const trimmed = slug.trim();
  if (trimmed) {
    sessionStorage.setItem(ENTERPRISE_TENANT_SLUG_KEY, trimmed);
  } else {
    sessionStorage.removeItem(ENTERPRISE_TENANT_SLUG_KEY);
  }
}

export function resolveEnterpriseApiKeyForTenant(slug: string | null): string {
  const primary = enterpriseApiKey();
  if (!slug) {
    return primary;
  }
  try {
    const raw = sessionStorage.getItem(ENTERPRISE_TENANT_KEYS_KEY);
    if (!raw) {
      return primary;
    }
    const map = JSON.parse(raw) as Record<string, string>;
    const mapped = map[slug];
    if (typeof mapped === "string" && mapped.trim()) {
      return mapped.trim();
    }
  } catch {
    /* ignore */
  }
  return primary;
}

export async function apiJsonEnterprise<T>(path: string, init: RequestInit = {}): Promise<T> {
  const slug = selectedEnterpriseTenantSlug();
  const key = resolveEnterpriseApiKeyForTenant(slug || null);
  if (!key) {
    throw new Error("Enterprise API key required (set in sign-in panel).");
  }
  return apiJson<T>(path, {
    ...init,
    headers: {
      "X-Nimbusware-Api-Key": key,
      ...(init.headers as Record<string, string>),
    },
  });
}

/** Admin JSON fetch — maps COMPUTE/CAPACITY=2 HTTP 503 problems to peel miss (`sak492-i`). */
export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...adminHeaders(),
      ...(init.headers as Record<string, string>),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    const mapped = mapHttp503PeelMiss(res.status, text);
    if (mapped) {
      return mapped as T;
    }
    const detail = parseApiErrorBody(text);
    const err = new Error(`${res.status}: ${String(detail).slice(0, 400)}`);
    (err as Error & { status?: number }).status = res.status;
    throw err;
  }
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

/** sak436-f: typed session compute status (broker-first). */
export type SessionComputeStatus = {
  session_id?: string;
  nodes?: Array<Record<string, unknown>>;
  queue_depth?: number;
  via?: string;
  status?: string;
  error?: string;
};

export async function getSessionComputeStatus(
  sessionId: string,
): Promise<SessionComputeStatus> {
  const raw = await apiJson<SessionComputeStatus>(
    `/chat/sessions/${encodeURIComponent(sessionId)}/compute/status`,
  );
  return normalizeStatusMiss(raw);
}

/** sak436-f: typed enterprise fleet-mesh status. */
export type FleetMeshStatus = {
  feature?: string;
  status?: string;
  nodes?: Array<Record<string, unknown>>;
  queue_depth?: number;
  via?: string;
  error?: string;
  session_id?: string;
};

export async function getFleetMeshStatus(
  sessionId?: string,
): Promise<FleetMeshStatus> {
  const q = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  const raw = await apiJsonEnterprise<FleetMeshStatus>(
    `/enterprise/fleet-mesh/status${q}`,
  );
  return normalizeStatusMiss(raw);
}

/** sak437-f: typed work-unit queue depth (Nimbusware proxy). */
export type WorkUnitQueueDepth = {
  queued?: number;
  session_id?: string | null;
  via?: string;
  status?: string;
  error?: string;
  feature?: string;
};

export async function getWorkUnitQueueDepth(
  sessionId?: string,
): Promise<WorkUnitQueueDepth> {
  const q = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  const raw = await apiJson<WorkUnitQueueDepth>(`/compute/work-units/queue${q}`);
  const miss = normalizeComputeActionMiss(raw as Record<string, unknown>);
  if (miss) {
    return {
      ...(miss as WorkUnitQueueDepth),
      queued: typeof raw.queued === "number" ? raw.queued : 0,
    };
  }
  return raw;
}

export type WorkUnitActionResponse = {
  work_unit?: Record<string, unknown> | null;
  via?: string;
  error?: string;
  status?: string;
  action?: string;
  feature?: string;
};

export async function enqueueWorkUnit(body: {
  run_id?: string;
  session_id?: string;
  stage_name?: string;
  agent_role?: string;
  kind?: string;
  payload?: Record<string, unknown>;
}): Promise<WorkUnitActionResponse> {
  const raw = await apiJson<Record<string, unknown>>("/compute/work-units/enqueue", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const miss = normalizeComputeActionMiss(raw);
  if (miss) {
    return miss as WorkUnitActionResponse;
  }
  return assertBrokerComputeRecordOk(raw, "work") as WorkUnitActionResponse;
}

export async function claimWorkUnit(nodeId: string): Promise<WorkUnitActionResponse> {
  const raw = await apiJson<Record<string, unknown>>("/compute/work-units/claim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ node_id: nodeId }),
  });
  if (isComputeMiss(raw)) {
    return raw as WorkUnitActionResponse;
  }
  // Empty poll: work_unit null + via=broker is success.
  if (raw.via === "broker" && (raw.work_unit == null || raw.work == null)) {
    return { ...raw, work_unit: (raw.work_unit as Record<string, unknown> | null) ?? null };
  }
  if (raw.work_unit && typeof raw.work_unit === "object") {
    return raw as WorkUnitActionResponse;
  }
  const normalized = normalizeClaimWorkResponse({
    work: raw.work_unit ?? raw.work ?? null,
    error: raw.error,
    via: raw.via,
  });
  return {
    ...raw,
    work_unit: (normalized.work as Record<string, unknown> | null) ?? null,
    via: String(normalized.via || raw.via || "broker"),
  };
}

export async function completeWorkUnit(
  workUnitId: string,
  body: { status?: string; result?: Record<string, unknown> } = {},
): Promise<WorkUnitActionResponse> {
  const raw = await apiJson<Record<string, unknown>>(
    `/compute/work-units/${encodeURIComponent(workUnitId)}/complete`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (isComputeMiss(raw)) {
    return raw as WorkUnitActionResponse;
  }
  return assertBrokerComputeRecordOk(raw, "work") as WorkUnitActionResponse;
}

export async function terminateRestartWorkUnit(
  workUnitId: string,
): Promise<WorkUnitActionResponse> {
  const raw = await apiJson<Record<string, unknown>>(
    `/compute/work-units/${encodeURIComponent(workUnitId)}/terminate-restart`,
    { method: "POST" },
  );
  if (isComputeMiss(raw)) {
    return raw as WorkUnitActionResponse;
  }
  // Requeue success may be work-shaped or action=requeue.
  if (raw.action === "requeue" || raw.work_unit != null || raw.work != null) {
    if (raw.work_unit != null || raw.work != null) {
      return assertBrokerComputeRecordOk(
        raw.work_unit != null ? raw : { ...raw, work: raw.work },
        "work",
      ) as WorkUnitActionResponse;
    }
    return raw as WorkUnitActionResponse;
  }
  return assertBrokerComputeRecordOk(raw, "work") as WorkUnitActionResponse;
}

export type ComputeNodeList = {
  nodes?: Array<Record<string, unknown>>;
  via?: string;
  error?: string;
  status?: string;
  feature?: string;
};

export async function listComputeNodes(sessionId?: string): Promise<ComputeNodeList> {
  const q = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  const raw = await apiJson<ComputeNodeList>(`/compute/nodes${q}`);
  if (isDomainPeelMiss(raw)) {
    return { ...raw, nodes: Array.isArray(raw.nodes) ? raw.nodes : [] };
  }
  return assertBrokerComputeListOk(raw, "nodes") as ComputeNodeList;
}

export async function registerComputeNode(body: {
  display_name?: string;
  host_label?: string;
  base_url: string;
  session_id?: string;
  capabilities?: Record<string, unknown>;
}): Promise<{ node?: Record<string, unknown>; via?: string; error?: string }> {
  const raw = await apiJson<Record<string, unknown>>("/compute/nodes/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const miss = normalizeComputeActionMiss(raw);
  if (miss) {
    return miss as { node?: Record<string, unknown>; via?: string; error?: string };
  }
  return assertBrokerComputeRecordOk(raw, "node") as {
    node?: Record<string, unknown>;
    via?: string;
    error?: string;
  };
}

export async function heartbeatComputeNode(
  nodeId: string,
  body: { status?: string; capabilities?: Record<string, unknown> } = {},
): Promise<{ node?: Record<string, unknown>; via?: string; error?: string }> {
  const raw = await apiJson<Record<string, unknown>>(
    `/compute/nodes/${encodeURIComponent(nodeId)}/heartbeat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  const miss = normalizeComputeActionMiss(raw);
  if (miss) {
    return miss as { node?: Record<string, unknown>; via?: string; error?: string };
  }
  return assertBrokerComputeRecordOk(raw, "node") as {
    node?: Record<string, unknown>;
    via?: string;
    error?: string;
  };
}

