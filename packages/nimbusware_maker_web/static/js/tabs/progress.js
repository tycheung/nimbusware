import { apiJson, toast } from "../api-client.js";
import { renderCriticReliabilityPanel, loadRunOrFleetCriticReliability } from "../critic-reliability-panel.js";
import { renderLaunchScorecard, fetchScorecardForRun } from "../launch-scorecard.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { openSseStream, parseSseJson, theaterLineText } from "../sse-client.js";
import { appendTheaterLine } from "../../../../nimbusware_ui_shared/js/theater-dom.js";
import { PROGRESS_MOUNT_HTML } from "./progress/template.js";
import { renderFindings, renderGateFailSteps } from "./progress/findings-gates.js";
import { renderProgressBody, loadCompletionEval } from "./progress/render-chips.js";
import { wireCompactToolbar, wireMobilePushPanel } from "./progress/compact-toolbar.js";
import { wireOperatorRibbons } from "./progress/operator-ribbons.js";
import {
  renderIntegratorRibbon,
  wireIntegratorRibbon,
} from "./progress/integrator-ribbon.js";
import { renderContextArtifacts, renderMemoryInfluence } from "./progress/context-panels.js";

let theaterHandle = null;
let progressHandle = null;

function stopStreams() {
  theaterHandle?.close();
  progressHandle?.close();
  theaterHandle = null;
  progressHandle = null;
}

function appendTheater(msg) {
  const list = document.getElementById("theater-list");
  appendTheaterLine(list, msg);
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
        if (scorecard) renderLaunchScorecard(scoreMount, scorecard, { testIdPrefix: "maker-completion" });
      }
    }
  }

  theaterHandle = openSseStream(`/runs/${id}/theater/stream`, {
    onEvent: {
      theater: (ev) => {
        const data = parseSseJson(ev);
        const text = theaterLineText(data);
        if (text) appendTheater(text);
      },
    },
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      const text = theaterLineText(data);
      if (text) appendTheater(text);
      else if (data?.messages) data.messages.forEach((m) => appendTheater(theaterLineText(m)));
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
    renderFindings(findingsBody.findings || []);
    await renderGateFailSteps(apiJson, id);
  } catch {
    renderFindings([]);
  }

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
