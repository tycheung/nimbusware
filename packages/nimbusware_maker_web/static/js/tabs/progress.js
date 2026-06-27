import { apiJson, toast } from "../api-client.js";
import { renderCriticReliabilityPanel, loadRunOrFleetCriticReliability } from "../critic-reliability-panel.js";
import { renderLaunchScorecard, fetchScorecardForRun, renderSurfaceLaunchSummary } from "../launch-scorecard.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { openSseStream, parseSseJson } from "../sse-client.js";
import { appendTheaterLine } from "../../../../nimbusware_ui_shared/js/theater-dom.js";
import { theaterPayloadFromSse } from "../theater-renderer.js";
import { PROGRESS_MOUNT_HTML } from "./progress/template.js";
import { renderFindings, renderGateFailSteps } from "./progress/findings-gates.js";
import { renderProgressBody, loadCompletionEval } from "./progress/render-chips.js";
import { wireCompactToolbar, wireMobilePushPanel } from "./progress/compact-toolbar.js";
import { wireOperatorRibbons } from "./progress/operator-ribbons.js";
import {
  renderIntegratorRibbon,
  wireIntegratorRibbon,
} from "./progress/integrator-ribbon.js";
import { wireDeployCockpit } from "../deploy_cockpit.js";
import { renderContextArtifacts, renderMemoryInfluence } from "./progress/context-panels.js";

let theaterHandle = null;
let progressHandle = null;
let lastFindings = [];
let autoLaunchCheckDone = false;

async function maybeAutoLaunchCheck(runId, body) {
  if (autoLaunchCheckDone || !runId) return;
  const cpState = String(body?.campaign_progress?.state || "").toLowerCase();
  const runStatus = String(body?.run_status || "").toLowerCase();
  const terminal =
    cpState === "completed" ||
    cpState === "failed" ||
    runStatus === "completed" ||
    runStatus === "failed";
  if (!terminal) return;
  const scoreMount = document.getElementById("completion-launch-scorecard");
  if (scoreMount?.querySelector("table")) {
    autoLaunchCheckDone = true;
    return;
  }
  autoLaunchCheckDone = true;
  try {
    const scorecard = await apiJson(`/runs/${encodeURIComponent(runId)}/maker/launch-eval`, {
      method: "POST",
    });
    if (scoreMount) {
      renderLaunchScorecard(scoreMount, scorecard, { testIdPrefix: "maker-completion" });
      renderSurfaceLaunchSummary(scoreMount, scorecard);
    }
    document.getElementById("completion-cockpit")?.removeAttribute("hidden");
  } catch {
    autoLaunchCheckDone = false;
  }
}

function stopStreams() {
  theaterHandle?.close();
  progressHandle?.close();
  theaterHandle = null;
  progressHandle = null;
}

function appendTheaterPayload(data) {
  const msg = theaterPayloadFromSse(data);
  if (!msg || (!msg.headline && !msg.body_md)) return;
  const list = document.getElementById("theater-list");
  appendTheaterLine(list, msg, {
    testid: msg.data_testid || "maker-progress-theater-line",
  });
}

function handleProgressTheaterEvent(data) {
  if (!data || typeof data !== "object") return;
  if (data.headline || data.body_md || data.actor_display) {
    appendTheaterPayload(data);
    return;
  }
  if (Array.isArray(data.messages)) {
    for (const row of data.messages) appendTheaterPayload(row);
  }
}

export async function mountProgress(root) {
  const mount = document.getElementById("progress-mount");
  if (mount) mount.innerHTML = PROGRESS_MOUNT_HTML;

  window.addEventListener("maker-route-leave-progress", stopStreams);

  let id = resolveRunId();
  if (!id) id = await hydrateActiveRun(apiJson);
  if (!id) return;

  const exportBar = document.createElement("p");
  exportBar.className = "actions";
  const exportLink = document.createElement("a");
  exportLink.href = `/v1/runs/${encodeURIComponent(id)}/theater/export`;
  exportLink.textContent = "Export theater transcript (.md)";
  exportLink.setAttribute("download", `nimbusware-theater-${id}.md`);
  mount?.prepend(exportBar);
  exportBar.appendChild(exportLink);

  wireCompactToolbar();
  wireMobilePushPanel();
  wireIntegratorRibbon();
  void renderIntegratorRibbon(id);
  wireDeployCockpit(id, { scope: "progress" });
  wireOperatorRibbons(id);

  async function enrichAndRenderProgress(body) {
    if (body?.campaign_progress) {
      body._completion_eval = await loadCompletionEval(id);
    }
    const runStatus = String(body?.run_status || "").toLowerCase();
    if (!body._completion_eval && (runStatus === "completed" || runStatus === "failed")) {
      body._completion_eval = await loadCompletionEval(id);
    }
    renderProgressBody(body);
    const terminal = runStatus === "completed" || runStatus === "failed";
    if (terminal) {
      const scoreMount = document.getElementById("completion-launch-scorecard");
      if (scoreMount && !scoreMount.querySelector("table")) {
        const scorecard = await fetchScorecardForRun(apiJson, id);
        if (scorecard) {
          renderLaunchScorecard(scoreMount, scorecard, { testIdPrefix: "maker-completion" });
          renderSurfaceLaunchSummary(scoreMount, scorecard);
        }
      }
      await maybeAutoLaunchCheck(id, body);
    }
  }

  theaterHandle = openSseStream(`/runs/${id}/theater/stream`, {
    onEvent: {
      theater: (ev) => {
        const data = parseSseJson(ev);
        if (data) handleProgressTheaterEvent(data);
      },
    },
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data) handleProgressTheaterEvent(data);
    },
  });

  progressHandle = openSseStream(`/runs/${id}/maker-progress/stream?simple=true`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data) enrichAndRenderProgress(data).catch(() => renderProgressBody(data));
    },
  });

  try {
    const snap = await apiJson(`/runs/${id}/maker-progress?simple=true`);
    await enrichAndRenderProgress(snap);
  } catch (e) {
    toast(String(e.message || e), "error");
  }

  const rubricLink = document.getElementById("completion-rubric-link");
  if (rubricLink) rubricLink.href = `#/review?run_id=${encodeURIComponent(id)}`;

  document.getElementById("completion-run-launch-check")?.addEventListener("click", async () => {
    const rid = resolveRunId() || id;
    if (!rid) return toast("No active run", "error");
    try {
      const scorecard = await apiJson(`/runs/${encodeURIComponent(rid)}/maker/launch-eval`, {
        method: "POST",
      });
      const scoreMount = document.getElementById("completion-launch-scorecard");
      if (scoreMount) renderLaunchScorecard(scoreMount, scorecard, { testIdPrefix: "maker-completion" });
      document.getElementById("completion-cockpit")?.removeAttribute("hidden");
      toast("Launch check complete", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  try {
    const criticBody = await loadRunOrFleetCriticReliability(apiJson, id);
    const criticPanel = document.getElementById("critic-reliability-panel");
    const criticMount = document.getElementById("critic-reliability-mount");
    if (criticPanel && criticMount && (criticBody.rows || []).length) {
      criticPanel.hidden = false;
      renderCriticReliabilityPanel(criticMount, criticBody, { testIdPrefix: "maker-progress-critic" });
    }
  } catch {
    /* optional */
  }

  try {
    const findingsBody = await apiJson(`/runs/${id}/findings`);
    lastFindings = findingsBody.findings || [];
    renderFindings(lastFindings);
    await renderGateFailSteps(apiJson, id);
  } catch {
    lastFindings = [];
    renderFindings([]);
  }

  document.getElementById("findings-show-all")?.addEventListener("change", () => {
    renderFindings(lastFindings);
  });

  try {
    const timeline = await apiJson(`/runs/${id}/timeline?limit=1`);
    const created = (timeline.events || []).find((e) => e.event_type === "run.created");
    const projectId = created?.metadata?.project?.id;
    if (projectId) await renderContextArtifacts(projectId);
  } catch {
    /* ignore */
  }

  await renderMemoryInfluence(id);
}

export function unmountProgress() {
  window.dispatchEvent(new Event("maker-route-leave-progress"));
}
