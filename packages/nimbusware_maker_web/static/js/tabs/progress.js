import { apiJson, toast } from "../api-client.js";
import { renderCriticReliabilityPanel, loadRunCriticReliability } from "../critic-reliability-panel.js";
import { renderLaunchScorecard } from "../launch-scorecard.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { openSseStream, parseSseJson } from "../sse-client.js";

const BLOCKING_SEVERITIES = new Set(["BLOCKER", "HIGH"]);

function reproSummary(steps) {
  if (!Array.isArray(steps) || !steps.length) return "";
  const joined = steps.map((s) => String(s).trim()).filter(Boolean).join(" → ");
  return joined.length > 160 ? `${joined.slice(0, 157)}…` : joined;
}

function renderFindings(findings) {
  const list = document.getElementById("findings-list");
  if (!list) return;
  list.replaceChildren();
  const blocked = (findings || []).filter((ev) => {
    const sev = String(ev?.payload?.severity || "").toUpperCase();
    return BLOCKING_SEVERITIES.has(sev);
  });
  const items = blocked.length ? blocked : findings || [];
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "finding-card finding-card--empty";
    li.textContent = "No blocking findings yet.";
    li.dataset.testid = "maker-findings-empty";
    list.appendChild(li);
    return;
  }
  for (const ev of items) {
    const pl = ev.payload || {};
    const sev = String(pl.severity || "unknown").toUpperCase();
    const li = document.createElement("li");
    li.className = `finding-card severity-${sev.toLowerCase()}`;
    li.dataset.testid = "maker-finding-card";
    const head = document.createElement("div");
    head.className = "finding-headline";
    head.dataset.testid = "maker-finding-headline";
    head.textContent = `${sev} · ${pl.category || "uncategorized"}`;
    li.appendChild(head);
    if (pl.owner_role) {
      const owner = document.createElement("p");
      owner.className = "muted finding-owner";
      owner.textContent = `Owner: ${pl.owner_role}`;
      li.appendChild(owner);
    }
    const repro = reproSummary(pl.repro_steps);
    if (repro) {
      const steps = document.createElement("p");
      steps.className = "finding-repro";
      steps.dataset.testid = "maker-finding-repro";
      steps.textContent = repro;
      li.appendChild(steps);
    }
    list.appendChild(li);
  }
}

let theaterHandle = null;
let progressHandle = null;

export async function mountProgress(root) {
  const mount = document.getElementById("progress-mount");
  if (mount) {
    mount.innerHTML = `
      <div id="compact-toolbar" class="actions" data-testid="maker-compact-toolbar" hidden>
        <button type="button" id="compact-all-btn">Compact all</button>
        <label>Last N <input type="number" id="compact-last-n" min="1" max="50" value="3" style="width:3rem" /></label>
        <button type="button" id="compact-last-n-btn">Compact last N</button>
        <button type="button" id="compact-selected-btn">Compact selected</button>
        <button type="button" id="compact-revert-btn">Revert last compaction</button>
      </div>
      <ul id="theater-list"></ul>
      <p id="pressure-banner" class="pressure-banner" hidden></p>
      <span id="context-budget-chip" class="context-budget-chip" hidden></span>
      <p id="factory-status-chip" class="factory-status-chip" hidden data-testid="maker-factory-status"></p>
      <p id="handoff-preview" class="handoff-preview" hidden></p>
      <p id="slice-summary"></p>
      <p id="campaign-controls" class="actions" hidden></p>
      <ol id="slice-list"></ol>
      <section id="completion-cockpit" class="completion-cockpit panel" data-testid="maker-completion-cockpit" hidden>
        <h4>Completion</h4>
        <p id="completion-terminal" data-testid="maker-completion-terminal"></p>
        <p id="completion-rationale" class="muted" data-testid="maker-completion-rationale"></p>
        <ul id="completion-blocking" data-testid="maker-completion-blocking"></ul>
        <div class="actions">
          <a id="completion-rubric-link" href="#/review" data-testid="maker-completion-rubric-link">Launch rubric (Review)</a>
          <button type="button" id="completion-run-launch-check" data-testid="maker-completion-run-launch-check">Run launch check</button>
        </div>
        <div id="completion-launch-scorecard" class="launch-scorecard" data-testid="maker-completion-launch-scorecard"></div>
      </section>
      <section id="critic-reliability-panel" class="panel" data-testid="maker-critic-reliability-panel" hidden>
        <h4>Critic reliability</h4>
        <div id="critic-reliability-mount"></div>
      </section>
      <section id="findings-workspace" class="findings-workspace" data-testid="maker-findings-workspace">
        <h4>Findings</h4>
        <ul id="findings-list"></ul>
      </section>
      <h4>Context artifacts</h4>
      <ul id="context-artifacts-list" class="context-artifacts-list"></ul>
      <h4>Memory influence</h4>
      <table id="memory-influence-table"><thead><tr><th>Stage</th><th>Hits</th><th>Digest</th></tr></thead><tbody></tbody></table>`;
  }

  function stopStreams() {
    theaterHandle?.close();
    progressHandle?.close();
    theaterHandle = null;
    progressHandle = null;
  }

  async function compactRun(body) {
    const rid = resolveRunId();
    if (!rid) return;
    try {
      await apiJson(`/runs/${encodeURIComponent(rid)}/compact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast("Context compacted", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  function wireCompactToolbar() {
    const bar = document.getElementById("compact-toolbar");
    if (!bar) return;
    bar.hidden = false;
    document.getElementById("compact-all-btn")?.addEventListener("click", () => compactRun({ scope: "all" }));
    document.getElementById("compact-last-n-btn")?.addEventListener("click", () => {
      const n = Number(document.getElementById("compact-last-n")?.value || 3);
      compactRun({ scope: "last_n", n });
    });
    document.getElementById("compact-selected-btn")?.addEventListener("click", () => {
      const refs = [...document.querySelectorAll("#theater-list input[data-theater-pick]:checked")]
        .map((el) => el.getAttribute("data-store-seq"))
        .filter(Boolean);
      if (!refs.length) {
        toast("Select theater messages first", "error");
        return;
      }
      compactRun({ scope: "source_refs", source_refs: refs });
    });
    document.getElementById("compact-revert-btn")?.addEventListener("click", async () => {
      const rid = resolveRunId();
      if (!rid) return;
      try {
        const budget = await apiJson(`/runs/${encodeURIComponent(rid)}/maker-progress`);
        const cid = budget?.context_budget?.last_compaction?.compaction_id;
        if (!cid) {
          toast("No compaction to revert", "error");
          return;
        }
        await apiJson(`/runs/${encodeURIComponent(rid)}/compactions/${encodeURIComponent(cid)}/revert`, {
          method: "POST",
        });
        toast("Compaction reverted", "success");
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
  }

  function appendTheater(msg) {
    const list = document.getElementById("theater-list");
    if (!list || !msg) return;
    const li = document.createElement("li");
    li.className = `theater-line severity-${msg.severity || "info"}`;
    if (msg.store_seq != null) {
      const pick = document.createElement("input");
      pick.type = "checkbox";
      pick.dataset.theaterPick = "1";
      pick.dataset.storeSeq = String(msg.store_seq);
      li.appendChild(pick);
    }
    const seq = msg.store_seq != null ? `#${msg.store_seq} ` : "";
    const headline = document.createElement("div");
    headline.className = "theater-headline";
    headline.textContent = `${seq}${msg.actor_display || "System"}: ${msg.headline || ""}`;
    if (msg.data_testid) li.dataset.testid = msg.data_testid;
    li.appendChild(headline);
    const body = (msg.body_md || "").trim();
    if (body) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "linkish theater-evidence-toggle";
      toggle.textContent = "Evidence";
      const pre = document.createElement("pre");
      pre.className = "theater-body";
      pre.hidden = true;
      pre.textContent = body;
      toggle.addEventListener("click", () => {
        pre.hidden = !pre.hidden;
        toggle.textContent = pre.hidden ? "Evidence" : "Hide";
      });
      headline.appendChild(document.createTextNode(" "));
      headline.appendChild(toggle);
      li.appendChild(pre);
    }
    list.appendChild(li);
  }

  function renderFactoryStatus(body) {
    const chip = document.getElementById("factory-status-chip");
    if (!chip) return;
    const fs = body.factory_status;
    if (!fs || !fs.tier) {
      chip.hidden = true;
      chip.textContent = "";
      return;
    }
    chip.hidden = false;
    const ism =
      fs.ism_coverage_pct != null ? ` · ISM ${Math.round(fs.ism_coverage_pct)}%` : "";
    const put =
      fs.put_e2e_passed == null ? "" : fs.put_e2e_passed ? " · PUT E2E pass" : " · PUT E2E fail";
    chip.replaceChildren();
    chip.appendChild(document.createTextNode(`Factory ${fs.tier}${ism}${put}`));
    const rid = resolveRunId();
    if (rid) {
      const link = document.createElement("a");
      link.href = `/v1/runs/${encodeURIComponent(rid)}/factory-evidence/export`;
      link.textContent = " · Download evidence";
      link.setAttribute("download", `factory-evidence-${rid}.zip`);
      link.dataset.testid = "maker-factory-evidence-download";
      chip.appendChild(link);
    }
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
    const last = budget.last_compaction;
    const compactHint =
      last && last.tokens_before != null && last.tokens_after != null
        ? ` · last compact ${last.tokens_before}→${last.tokens_after} tok`
        : "";
    chip.textContent = `Context ${pct}% (${budget.estimated_tokens}/${budget.window_tokens} tok)${compactHint}`;
    chip.title = "Advisory estimate of planner-facing context vs model window";
    chip.dataset.testid = "maker-context-budget-chip";
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
    const rid = resolveRunId();
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
      pause.dataset.testid = "maker-campaign-pause";
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

  function renderCompletion(completionPayload, cp) {
    const panel = document.getElementById("completion-cockpit");
    if (!panel) return;
    const show = Boolean(cp?.state) || Boolean(completionPayload);
    panel.hidden = !show;
    if (!show) return;

    const terminal = document.getElementById("completion-terminal");
    const rationale = document.getElementById("completion-rationale");
    const blocking = document.getElementById("completion-blocking");
    const state = String(cp?.state || bodyRunStatus(completionPayload) || "executing");
    if (terminal) {
      terminal.textContent = `Campaign: ${state}`;
      terminal.dataset.state = state;
    }
    const latest = completionPayload || {};
    if (rationale) {
      rationale.textContent = latest.rationale || "";
      rationale.hidden = !latest.rationale;
    }
    if (blocking) {
      blocking.replaceChildren();
      const findings = latest.blocking_findings || [];
      if (!findings.length) {
        const li = document.createElement("li");
        li.className = "muted";
        li.textContent = latest.verdict ? `Verdict: ${latest.verdict}` : "No blocking findings recorded.";
        blocking.appendChild(li);
      } else {
        for (const item of findings) {
          const li = document.createElement("li");
          li.textContent = String(item);
          blocking.appendChild(li);
        }
      }
    }
  }

  function bodyRunStatus(completionPayload) {
    if (!completionPayload) return "";
    const verdict = String(completionPayload.verdict || "").toUpperCase();
    if (verdict === "PASS") return "completed";
    if (verdict === "FAIL") return "failed";
    return "";
  }

  async function loadCompletionEval(runId) {
    try {
      const body = await apiJson(`/campaigns/${encodeURIComponent(runId)}/progress`);
      const evals = body.completion_evaluations || [];
      return evals.length ? evals[evals.length - 1] : null;
    } catch {
      return null;
    }
  }

  function renderProgress(body) {
    const summary = document.getElementById("slice-summary");
    const list = document.getElementById("slice-list");
    renderPressure(body);
    renderFactoryStatus(body);
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
    const handoffMount = document.getElementById("handoff-preview");
    const handoff = body.latest_handoff;
    if (handoffMount) {
      if (handoff && handoff.summary) {
        handoffMount.hidden = false;
        const preview = String(handoff.summary).slice(0, 200);
        handoffMount.textContent = `Latest handoff: ${preview}`;
        handoffMount.dataset.testid = "maker-latest-handoff";
      } else {
        handoffMount.hidden = true;
        handoffMount.textContent = "";
      }
    }
    if (body._completion_eval != null || body.campaign_progress) {
      renderCompletion(body._completion_eval, body.campaign_progress);
    }
  }

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

  theaterHandle = openSseStream(`/runs/${id}/theater/stream`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data?.message) appendTheater(data.message);
      else if (data?.messages) data.messages.forEach(appendTheater);
    },
  });

  async function enrichAndRenderProgress(body) {
    if (body?.campaign_progress) {
      body._completion_eval = await loadCompletionEval(id);
    }
    renderProgress(body);
  }

  progressHandle = openSseStream(`/runs/${id}/maker-progress/stream?simple=true`, {
    onMessage: (ev) => {
      const data = parseSseJson(ev);
      if (data) enrichAndRenderProgress(data).catch(() => renderProgress(data));
    },
  });

  try {
    const snap = await apiJson(`/runs/${id}/maker-progress?simple=true`);
    await enrichAndRenderProgress(snap);
  } catch (e) {
    toast(String(e.message || e), "error");
  }

  const rubricLink = document.getElementById("completion-rubric-link");
  if (rubricLink) {
    rubricLink.href = `#/review?run_id=${encodeURIComponent(id)}`;
  }
  document.getElementById("completion-run-launch-check")?.addEventListener("click", async () => {
    const rid = resolveRunId() || id;
    if (!rid) return toast("No active run", "error");
    try {
      const scorecard = await apiJson(`/runs/${encodeURIComponent(rid)}/maker/launch-eval`, {
        method: "POST",
      });
      const mount = document.getElementById("completion-launch-scorecard");
      if (mount) renderLaunchScorecard(mount, scorecard, { testIdPrefix: "maker-completion" });
      document.getElementById("completion-cockpit")?.removeAttribute("hidden");
      toast("Launch check complete", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  try {
    const criticBody = await loadRunCriticReliability(apiJson, id);
    const criticPanel = document.getElementById("critic-reliability-panel");
    const criticMount = document.getElementById("critic-reliability-mount");
    if (criticPanel && criticMount && (criticBody.rows || []).length) {
      criticPanel.hidden = false;
      renderCriticReliabilityPanel(criticMount, criticBody, { testIdPrefix: "maker-progress-critic" });
    }
  } catch {
    /* optional when run has no critic events */
  }

  try {
    const findingsBody = await apiJson(`/runs/${id}/findings`);
    renderFindings(findingsBody.findings || []);
  } catch {
    renderFindings([]);
  }

  async function renderContextArtifacts(projectId) {
    const list = document.getElementById("context-artifacts-list");
    if (!list || !projectId) return;
    try {
      const body = await apiJson(`/projects/${encodeURIComponent(projectId)}/context-artifacts`);
      list.replaceChildren();
      const artifacts = body.artifacts || [];
      if (!artifacts.length) {
        const li = document.createElement("li");
        li.className = "context-artifact-empty";
        li.textContent = "No context artifacts";
        list.appendChild(li);
        return;
      }
      for (const art of artifacts) {
        const li = document.createElement("li");
        li.dataset.testid = "maker-context-artifact";
        li.textContent = `${art.title || art.artifact_id} (${art.kind || "note"})`;
        li.title = String(art.content || "").slice(0, 400);
        list.appendChild(li);
      }
    } catch {
      list.replaceChildren();
    }
  }

  try {
    const timeline = await apiJson(`/runs/${id}/timeline?limit=1`);
    const created = (timeline.events || []).find((e) => e.event_type === "run.created");
    const projectId = created?.metadata?.project?.id;
    if (projectId) await renderContextArtifacts(projectId);
  } catch {
    /* optional when run has no linked project */
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
