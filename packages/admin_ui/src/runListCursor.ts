/** Keyset cursor codec matching Python _encode_run_list_cursor / _decode_run_list_cursor. */

export function encodeRunListCursor(seq: number, runId: string): string {
  const raw = JSON.stringify({ s: seq, r: runId });
  const b64 = btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return b64;
}

export function decodeRunListCursor(value: string): { seq: number; runId: string } {
  const pad = "=".repeat((4 - (value.length % 4)) % 4);
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/") + pad;
  const parsed = JSON.parse(atob(normalized)) as { s: number; r: string };
  return { seq: Number(parsed.s), runId: String(parsed.r) };
}

export type RunListFilters = {
  limit: number;
  status: string;
  workflow_profile: string;
  cursor: string;
};

export function filtersFromSearch(search: string): RunListFilters {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  return {
    limit: Math.min(200, Math.max(1, Number(params.get("limit") || "50"))),
    status: params.get("status") || "",
    workflow_profile: params.get("workflow_profile") || "",
    cursor: params.get("cursor") || "",
  };
}

export function buildRunsQuery(filters: RunListFilters): string {
  const pairs: [string, string][] = [["limit", String(filters.limit)], ["include_summary", "1"]];
  if (filters.status) pairs.push(["status", filters.status]);
  if (filters.workflow_profile) pairs.push(["workflow_profile", filters.workflow_profile]);
  if (filters.cursor) {
    pairs.push(["cursor", filters.cursor]);
    pairs.push(["offset", "0"]);
  }
  return pairs.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
}

export function syncFiltersToUrl(filters: RunListFilters) {
  const params = new URLSearchParams();
  if (filters.limit !== 50) params.set("limit", String(filters.limit));
  if (filters.status) params.set("status", filters.status);
  if (filters.workflow_profile) params.set("workflow_profile", filters.workflow_profile);
  if (filters.cursor) params.set("cursor", filters.cursor);
  const qs = params.toString();
  const path = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
  window.history.replaceState({}, "", path);
}
