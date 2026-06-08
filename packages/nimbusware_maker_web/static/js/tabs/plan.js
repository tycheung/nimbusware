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

function sliceBadge(status) {
  const raw = String(status || "pending");
  const cls = SLICE_STATUS_CLASS[raw] || "slice-badge--pending";
  return `<span class="slice-badge ${cls}" data-testid="maker-plan-slice-badge">${raw}</span>`;
}

function renderTree(root, tree) {
  const epics = tree.epics || [];
  const summary = tree.summary || {};
  if (!epics.length) {
    root.innerHTML =
      "<p class='muted' data-testid='maker-plan-empty'>No backlog yet — start a campaign from Build.</p>";
    return;
  }
  const parts = [
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
        `<details class="plan-feature">
          <summary><em>${feature.title}</em> (${(feature.slices || []).length} slices)</summary>
          <ul class="plan-slice-list">`,
      );
      for (const slice of feature.slices || []) {
        const rationale = String(slice.rationale || "").slice(0, 120);
        parts.push(
          `<li data-testid="maker-plan-slice">
            ${sliceBadge(slice.status)} <code>${slice.slice_id}</code>
            ${rationale ? `<span class="muted plan-rationale">${rationale}</span>` : ""}
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
    const tree = await apiJson(`/campaigns/${encodeURIComponent(runId)}/backlog`);
    renderTree(root, tree);
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
