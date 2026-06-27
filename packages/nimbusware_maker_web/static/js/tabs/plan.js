import { apiJson } from "../api-client.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { openSseStream, parseSseJson } from "../sse-client.js";

const SLICE_STATUS_CLASS = {
  passed: "slice-badge--passed",
  PASSED: "slice-badge--passed",
  pending: "slice-badge--pending",
  PENDING: "slice-badge--pending",
  in_flight: "slice-badge--active",
  IN_FLIGHT: "slice-badge--active",
  failed: "slice-badge--failed",
  FAILED: "slice-badge--failed",
};

const SURFACE_LABEL = {
  api: "API",
  web: "Web",
  infra: "Infra",
  contract: "Contract",
};

export function surfaceBadge(surfaceId) {
  const raw = String(surfaceId || "").trim().toLowerCase();
  if (!raw) return "";
  const label = SURFACE_LABEL[raw] || raw.toUpperCase();
  return `<span class="surface-badge surface-badge--${raw}" data-testid="maker-plan-surface-badge" data-surface="${raw}">${label}</span>`;
}

function sliceBadge(status) {
  const raw = String(status || "pending");
  const cls = SLICE_STATUS_CLASS[raw] || "slice-badge--pending";
  return `<span class="slice-badge ${cls}" data-testid="maker-plan-slice-badge">${raw}</span>`;
}

export function contractGateFromTimeline(events) {
  let state = "pending";
  let detail = "Contract gate not run yet";
  for (const ev of events || []) {
    if (ev.event_type !== "stage.passed" && ev.event_type !== "stage.failed") continue;
    const stage = String(ev.payload?.stage_name || "");
    if (stage !== "slice.contract") continue;
    state = ev.event_type === "stage.passed" ? "passed" : "failed";
    detail =
      ev.metadata?.detail ||
      ev.payload?.detail ||
      ev.payload?.message ||
      (state === "passed" ? "Contract artifacts verified" : "Contract check failed");
    break;
  }
  return { state, detail };
}

function contractGateCard(gate) {
  const state = gate?.state || "pending";
  const detail = gate?.detail || "";
  return `<section class="plan-contract-gate panel" data-testid="maker-plan-contract-gate" data-state="${state}">
    <h4>Contract gate</h4>
    <p class="plan-contract-status" data-testid="maker-plan-contract-status">${state}</p>
    ${detail ? `<p class="muted plan-contract-detail" data-testid="maker-plan-contract-detail">${detail}</p>` : ""}
  </section>`;
}

function renderTree(root, tree, contractGate) {
  const epics = tree.epics || [];
  const summary = tree.summary || {};
  if (!epics.length) {
    root.innerHTML =
      "<p class='muted' data-testid='maker-plan-empty'>No backlog yet — start a campaign from Build.</p>";
    return;
  }
  const parts = [
    contractGate ? contractGateCard(contractGate) : "",
    `<div class="plan-toolbar actions">
      <span class="plan-summary muted" data-testid="maker-plan-summary">
        ${summary.slices_completed ?? 0}/${summary.total_slices ?? "?"} slices complete
      </span>
      <button type="button" id="plan-refresh" data-testid="maker-plan-refresh">Refresh</button>
    </div>`,
    "<div class='plan-tree' data-testid='maker-plan-tree'>",
  ];
  for (const epic of epics) {
    parts.push(
      `<details class="plan-epic" open data-testid="maker-plan-epic">
        <summary><strong>${epic.title}</strong> <span class="epic-status">${epic.status || ""}</span></summary>`,
    );
    for (const feature of epic.features || []) {
      parts.push(
        `<details class="plan-feature" open>
          <summary><em>${feature.title}</em> (${(feature.slices || []).length} slices)</summary>
          <ul class="plan-slice-list">`,
      );
      for (const slice of feature.slices || []) {
        const rationale = String(slice.rationale || "").slice(0, 120);
        const steer =
          slice.status === "pending" || slice.status === "PENDING"
            ? `<button type="button" class="linkish plan-steer-btn" data-slice-id="${slice.slice_id}" data-testid="maker-plan-steer-${slice.slice_id}">Steer</button>`
            : "";
        const stackHint = slice.stack_id
          ? `<span class="muted plan-stack" data-testid="maker-plan-stack">${slice.stack_id}</span>`
          : "";
        parts.push(
          `<li data-testid="maker-plan-slice">
            ${surfaceBadge(slice.surface_id)}
            ${sliceBadge(slice.status)} <code>${slice.slice_id}</code>
            ${stackHint}
            ${rationale ? `<span class="muted plan-rationale">${rationale}</span>` : ""}
            ${steer}
          </li>`,
        );
      }
      parts.push("</ul></details>");
    }
    parts.push("</details>");
  }
  parts.push("</div>");
  root.innerHTML = parts.join("");
  root.querySelector("#plan-refresh")?.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("maker-plan-refresh"));
  });
  root.querySelectorAll(".plan-steer-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const runId = resolveRunId();
      const sliceId = btn.getAttribute("data-slice-id") || "";
      const msg = sliceId ? `[steer] Focus backlog slice ${sliceId}` : "[steer]";
      if (runId) {
        window.location.hash = `/chat?run_id=${encodeURIComponent(runId)}`;
      } else {
        window.location.hash = "/chat";
      }
      sessionStorage.setItem("maker_plan_steer_draft", msg);
    });
  });
}

let planStreamHandle = null;
let planPollTimer = null;

function stopPlanRefresh() {
  planStreamHandle?.close();
  planStreamHandle = null;
  if (planPollTimer) {
    clearInterval(planPollTimer);
    planPollTimer = null;
  }
}

async function loadBacklog(root, runId) {
  try {
    const [tree, timeline] = await Promise.all([
      apiJson(`/campaigns/${encodeURIComponent(runId)}/backlog`),
      apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=120`).catch(() => ({ events: [] })),
    ]);
    const contractGate = contractGateFromTimeline(timeline.events || []);
    renderTree(root, tree, contractGate);
    return true;
  } catch (err) {
    root.innerHTML = `<p class='muted' data-testid='maker-plan-pending'>Backlog not available yet (${err.message || "pending"}).</p>`;
    return false;
  }
}

export async function mountPlan(root) {
  stopPlanRefresh();
  root.innerHTML = "<p class='muted'>Loading backlog…</p>";

  let runId = resolveRunId();
  if (!runId) runId = await hydrateActiveRun(apiJson);
  if (!runId) {
    root.innerHTML =
      "<p class='muted' data-testid='maker-plan-no-run'>Open a run from Progress or Review to view the plan.</p>";
    return;
  }

  await loadBacklog(root, runId);

  const onRefresh = () => {
    loadBacklog(root, runId).catch(() => {});
  };
  window.addEventListener("maker-plan-refresh", onRefresh);

  planStreamHandle = openSseStream(`/runs/${encodeURIComponent(runId)}/maker-progress/stream?simple=true`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data?.campaign_progress || data?.run_status) onRefresh();
    },
  });

  planPollTimer = setInterval(onRefresh, 30_000);

  window.addEventListener("maker-route-leave-plan", stopPlanRefresh, { once: true });
}

export function unmountPlan() {
  window.dispatchEvent(new Event("maker-route-leave-plan"));
}
