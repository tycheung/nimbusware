/**
 * Per-project active run_id in sessionStorage — reduces UUID paste across Maker tabs.
 */

const ACTIVE_RUN_PREFIX = "maker_active_run_id:";
const ACTIVE_PROJECT_KEY = "maker_active_project_id";

export function getActiveProjectId() {
  return sessionStorage.getItem(ACTIVE_PROJECT_KEY) || "";
}

export function setActiveProjectId(projectId) {
  if (!projectId) return;
  sessionStorage.setItem(ACTIVE_PROJECT_KEY, String(projectId));
}

function storageKey(projectId) {
  return `${ACTIVE_RUN_PREFIX}${projectId}`;
}

export function getStoredRunId(projectId = getActiveProjectId()) {
  if (!projectId) return "";
  return sessionStorage.getItem(storageKey(projectId)) || "";
}

export function setActiveRun(projectId, runId) {
  if (!projectId || !runId) return;
  sessionStorage.setItem(storageKey(String(projectId)), String(runId));
}

export function syncRunIdToShell(runId) {
  const value = String(runId || "");
  const canonical = document.getElementById("run-theater-run-id");
  if (canonical) canonical.value = value;
  for (const id of ["mobile-run-id", "desktop-run-id"]) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }
}

export function resolveRunId() {
  const search = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const fromUrl = search.get("run_id") || hashParams.get("run_id");
  if (fromUrl?.trim()) return fromUrl.trim();

  const fromField =
    document.getElementById("run-theater-run-id")?.value?.trim() ||
    document.getElementById("desktop-run-id")?.value?.trim() ||
    document.getElementById("mobile-run-id")?.value?.trim() ||
    "";
  if (fromField) return fromField;

  return getStoredRunId().trim();
}

function projectIdFromSummary(summary) {
  const meta = summary?.run_created_metadata;
  if (!meta || typeof meta !== "object") return "";
  if (meta.project_id != null && String(meta.project_id).trim()) {
    return String(meta.project_id).trim();
  }
  const project = meta.project;
  if (project && typeof project === "object" && project.id != null) {
    return String(project.id).trim();
  }
  return "";
}

export async function fetchActiveRunForProject(projectId, apiJson) {
  if (!projectId) return null;

  const stored = getStoredRunId(projectId);
  if (stored) return stored;

  try {
    const body = await apiJson("/runs?status=running&include_summary=1&limit=50");
    const matches = [];
    for (const rid of body.run_ids || []) {
      const summary = body.summaries?.[rid];
      if (projectIdFromSummary(summary) === String(projectId)) {
        matches.push(rid);
      }
    }
    if (matches.length) return matches[0];
    if ((body.run_ids || []).length === 1) return body.run_ids[0];
  } catch {
    /* optional when store is empty */
  }
  return null;
}

export async function hydrateActiveRun(apiJson) {
  const projectId = getActiveProjectId();
  const existing = resolveRunId();
  if (existing) {
    if (projectId) setActiveRun(projectId, existing);
    syncRunIdToShell(existing);
    return existing;
  }

  const rid = await fetchActiveRunForProject(projectId, apiJson);
  if (rid) {
    if (projectId) setActiveRun(projectId, rid);
    syncRunIdToShell(rid);
    return rid;
  }
  return "";
}

export function persistRunIdFromUrl() {
  const search = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const runId = search.get("run_id") || hashParams.get("run_id");
  if (!runId?.trim()) return;
  const projectId = getActiveProjectId();
  if (projectId) setActiveRun(projectId, runId.trim());
  syncRunIdToShell(runId.trim());
}
