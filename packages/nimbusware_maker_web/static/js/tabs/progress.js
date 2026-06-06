import { apiJson, toast } from "../api-client.js";
import { openSseStream, parseSseJson } from "../sse-client.js";

function runId() {
  return document.getElementById("run-theater-run-id")?.value?.trim() || "";
}

let theaterHandle = null;
let progressHandle = null;

export async function mountProgress(root) {
  const mount = document.getElementById("progress-mount");
  if (mount) {
    mount.innerHTML = `
      <ul id="theater-list"></ul>
      <p id="pressure-banner" class="pressure-banner" hidden></p>
      <span id="context-budget-chip" class="context-budget-chip" hidden></span>
      <p id="slice-summary"></p>
      <p id="campaign-controls" class="actions" hidden></p>
      <ol id="slice-list"></ol>
      <h4>Memory influence</h4>
      <table id="memory-influence-table"><thead><tr><th>Stage</th><th>Hits</th><th>Digest</th></tr></thead><tbody></tbody></table>`;
  }

  function stopStreams() {
    theaterHandle?.close();
    progressHandle?.close();
    theaterHandle = null;
    progressHandle = null;
  }

  function appendTheater(msg) {
    const list = document.getElementById("theater-list");
    if (!list || !msg) return;
    const li = document.createElement("li");
    li.textContent = `${msg.actor_display || "System"}: ${msg.headline || ""}`;
    list.appendChild(li);
  }

  function renderContextBudget(body) {
    const chip = document.getElementById("context-budget-chip");
    if (!chip) return;
    const budget = body.context_budget;
    if (!budget || !budget.window_tokens) {
      chip.hidden = true;
      chip.textContent = "";
      chip.dataset.level = "";
      return;
    }
    const pct = Math.round((budget.utilization_ratio || 0) * 100);
    chip.hidden = false;
    chip.dataset.level = budget.advisory_level || "green";
    chip.textContent = `Context ${pct}% (${budget.estimated_tokens}/${budget.window_tokens} tok)`;
    chip.title = "Advisory estimate of planner-facing context vs model window";
  }

  function renderPressure(body) {
    const banner = document.getElementById("pressure-banner");
    if (!banner) return;
    const p = body.resource_pressure;
    if (!p || p.level === "ok") {
      banner.hidden = true;
      banner.textContent = "";
      return;
    }
    banner.hidden = false;
    banner.textContent = p.headline || `Resource pressure: ${p.level}`;
    banner.dataset.level = p.level || "";
  }

  async function campaignAction(path, label) {
    const rid = runId();
    if (!rid) return;
    try {
      await apiJson(`/campaigns/${encodeURIComponent(rid)}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason_code: "maker_progress" }),
      });
      toast(`${label} ok`, "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  function renderCampaignControls(cp) {
    const bar = document.getElementById("campaign-controls");
    if (!bar) return;
    if (!cp || !cp.state) {
      bar.hidden = true;
      bar.replaceChildren();
      return;
    }
    bar.hidden = false;
    bar.replaceChildren();
    const state = String(cp.state || "");
    if (state !== "paused" && state !== "completed" && state !== "failed") {
      const pause = document.createElement("button");
      pause.type = "button";
      pause.textContent = "Pause campaign";
      pause.addEventListener("click", () => campaignAction("pause", "Pause"));
      bar.appendChild(pause);
    }
    if (state === "paused") {
      const resume = document.createElement("button");
      resume.type = "button";
      resume.textContent = "Resume campaign";
      resume.addEventListener("click", () => campaignAction("resume", "Resume"));
      bar.appendChild(resume);
    }
    if (state !== "completed" && state !== "failed") {
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "Cancel campaign";
      cancel.addEventListener("click", () => campaignAction("cancel", "Cancel"));
      bar.appendChild(cancel);
    }
  }

  function renderProgress(body) {
    const summary = document.getElementById("slice-summary");
    const list = document.getElementById("slice-list");
    renderPressure(body);
    renderContextBudget(body);
    if (summary) {
      const cp = body.campaign_progress;
      renderCampaignControls(cp);
      if (cp && cp.state) {
        summary.textContent = `${body.current_headline || ""} [campaign: ${cp.state}, ${cp.slices_completed || 0}/${cp.slices_total || "?"} slices]`.trim();
      } else {
        summary.textContent = body.current_headline || body.run_status || "";
      }
    }
    if (list) {
      list.replaceChildren();
      for (const s of body.slices || []) {
        const li = document.createElement("li");
        li.textContent = `${s.headline || s.slice_id} — ${s.status || s.state || ""}`;
        list.appendChild(li);
      }
    }
  }

  window.addEventListener("maker-route-leave-progress", stopStreams);

  const id = runId();
  if (!id) return;

  const exportBar = document.createElement("p");
  exportBar.className = "actions";
  const exportLink = document.createElement("a");
  exportLink.href = `/v1/runs/${encodeURIComponent(id)}/theater/export`;
  exportLink.textContent = "Export theater transcript (.md)";
  exportLink.setAttribute("download", `nimbusware-theater-${id}.md`);
  mount?.prepend(exportBar);
  exportBar.appendChild(exportLink);

  theaterHandle = openSseStream(`/runs/${id}/theater/stream`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data?.message) appendTheater(data.message);
      else if (data?.messages) data.messages.forEach(appendTheater);
    },
  });

  progressHandle = openSseStream(`/runs/${id}/maker-progress/stream?simple=true`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data) renderProgress(data);
    },
  });

  try {
    const snap = await apiJson(`/runs/${id}/maker-progress?simple=true`);
    renderProgress(snap);
  } catch (e) {
    toast(String(e.message || e), "error");
  }

  try {
    const mem = await apiJson(`/runs/${id}/memory-influence`);
    const tbody = document.querySelector("#memory-influence-table tbody");
    if (tbody) {
      tbody.replaceChildren();
      for (const row of mem.rows || []) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${row.stage || ""}</td><td>${row.hits || ""}</td><td>${row.query_digest || ""}</td>`;
        tbody.appendChild(tr);
      }
    }
  } catch {
    /* optional panel when run has no retrieval events */
  }
}

export function unmountProgress() {
  window.dispatchEvent(new Event("maker-route-leave-progress"));
}
