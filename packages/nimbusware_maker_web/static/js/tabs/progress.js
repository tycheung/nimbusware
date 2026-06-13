import { apiJson, toast } from "../api-client.js";
import { renderCriticReliabilityPanel, loadRunCriticReliability } from "../critic-reliability-panel.js";
import { renderLaunchScorecard } from "../launch-scorecard.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { openSseStream, parseSseJson, theaterLineText } from "../sse-client.js";

const BLOCKING_SEVERITIES = new Set(["BLOCKER", "HIGH"]);

const AUTOPILOT_CHECKPOINT_CATALOG = [
  "stop_after_run_plan",
  "stop_after_slice_plan",
  "stop_before_workspace_apply",
  "stop_on_slice_test_fail",
  "stop_on_dev_env_regression_fail",
  "stop_on_ui_regression_fail",
  "stop_on_gate_fail",
  "stop_before_factory_complete",
  "stop_at_terminal_review",
];

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
    if (BLOCKING_SEVERITIES.has(sev)) {
      const actions = document.createElement("div");
      actions.className = "finding-actions actions";
      const interject = document.createElement("button");
      interject.type = "button";
      interject.textContent = "Interject fix";
      interject.dataset.testid = "maker-finding-action-interject";
      interject.onclick = () => {
        const input = document.getElementById("interjection-message");
        if (input) {
          input.focus();
          input.value = `[steer] Address: ${pl.summary || pl.category || "gate failure"}`;
        }
      };
      actions.appendChild(interject);
      const widen = document.createElement("button");
      widen.type = "button";
      widen.textContent = "Widen in Chat";
      widen.dataset.testid = "maker-finding-action-widen";
      widen.onclick = () => {
        window.location.hash = "/chat?intent=slice";
      };
      actions.appendChild(widen);
      li.appendChild(actions);
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
        <button type="button" id="compact-save-artifact-btn" data-testid="maker-compact-save-artifact">Save compaction as artifact</button>
        <button type="button" id="compact-revert-btn">Revert last compaction</button>
      </div>
      <section id="integrator-ribbon" class="panel integrator-ribbon" data-testid="maker-integrator-ribbon">
        <h4>Integrator &amp; stitch</h4>
        <p id="integrator-ribbon-body" class="muted"></p>
        <div class="actions">
          <button type="button" id="integrator-stitch-refresh" data-testid="maker-integrator-stitch-refresh">Refresh stitch candidates</button>
          <button type="button" id="integrator-stitch-promote-batch" data-testid="maker-integrator-stitch-promote-batch">Promote pending batch</button>
        </div>
      </section>
      <section id="dev-env-ribbon" class="panel" data-testid="maker-dev-env-ribbon">
        <h4>Dev environment</h4>
        <p id="dev-env-status-body" class="muted"></p>
        <p id="dev-env-regression-detail" class="muted" data-testid="maker-dev-env-regression-detail"></p>
        <div class="actions">
          <button type="button" id="dev-env-start-btn" data-testid="maker-dev-env-start">Start session</button>
          <button type="button" id="dev-env-stop-btn" data-testid="maker-dev-env-stop">Stop session</button>
          <button type="button" id="dev-env-regression-btn" data-testid="maker-dev-env-regression">Run regression</button>
        </div>
      </section>
      <section id="interjection-ribbon" class="panel" data-testid="maker-interjection-ribbon">
        <h4>Interjection queue</h4>
        <textarea id="interjection-message" rows="2" placeholder="Steer the next slice…" data-testid="maker-interjection-input"></textarea>
        <div class="actions">
          <button type="button" id="interjection-next-btn" data-testid="maker-interjection-next">Next in queue</button>
          <button type="button" id="interjection-last-btn" data-testid="maker-interjection-last">Last in queue</button>
        </div>
        <p id="interjection-queue-body" class="muted"></p>
      </section>
      <section id="autopilot-ribbon" class="panel" data-testid="maker-autopilot-ribbon">
        <h4>Autopilot</h4>
        <label>Level 0–10 <input type="range" id="autopilot-slider" min="0" max="10" value="5" data-testid="maker-autopilot-slider" /></label>
        <span id="autopilot-level-label">5</span>
        <div id="autopilot-checkpoints" class="autopilot-checkpoints" data-testid="maker-autopilot-checkpoints"></div>
        <div class="actions">
          <label>Saved profile
            <select id="autopilot-profile-select" data-testid="maker-autopilot-profile-select">
              <option value="">— custom —</option>
            </select>
          </label>
          <button type="button" id="autopilot-profile-save-btn" data-testid="maker-autopilot-profile-save">Save profile</button>
          <button type="button" id="autopilot-save-btn" data-testid="maker-autopilot-save">Apply to run</button>
        </div>
      </section>
      <section id="learnings-ribbon" class="panel" data-testid="maker-learnings-ribbon">
        <h4>Learnings</h4>
        <p id="stitch-suggestion" class="hint" hidden data-testid="maker-stitch-suggestion"></p>
        <ul id="learnings-list" data-testid="maker-learnings-list"></ul>
      </section>
      <section id="variant-ribbon" class="panel" data-testid="maker-variant-ribbon">
        <h4>Variant arena</h4>
        <p id="variant-body" class="muted" data-testid="maker-variant-body">No variant experiments yet</p>
        <ul id="variant-list" class="variant-list" data-testid="maker-variant-list"></ul>
      </section>
      <section id="council-ribbon" class="panel" data-testid="maker-council-ribbon" hidden>
        <h4>Improvement council</h4>
        <p id="council-body" class="muted"></p>
      </section>
      <ul id="theater-list"></ul>
      <p id="pressure-banner" class="pressure-banner" hidden></p>
      <span id="work-type-badge" class="work-type-badge" hidden data-testid="maker-work-type-badge"></span>
      <span id="context-budget-chip" class="context-budget-chip" hidden></span>
      <p id="factory-status-chip" class="factory-status-chip" hidden data-testid="maker-factory-status"></p>
      <p id="gate-summary-banner" class="gate-summary-banner" hidden></p>
      <span id="role-cost-chip" class="role-cost-chip" hidden></span>
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
      <table id="memory-influence-table" data-testid="maker-memory-influence-table"><thead><tr><th>Stage</th><th>Hits</th><th>Digest</th></tr></thead><tbody></tbody></table>`;
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
    document.getElementById("compact-save-artifact-btn")?.addEventListener("click", async () => {
      const rid = resolveRunId();
      if (!rid) return;
      try {
        const out = await apiJson(`/runs/${encodeURIComponent(rid)}/context-artifacts/from-compaction`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        toast(`Saved artifact ${out.title || out.artifact_id}`, "success");
        const timeline = await apiJson(`/runs/${encodeURIComponent(rid)}/timeline?limit=1`);
        const created = (timeline.events || []).find((e) => e.event_type === "run.created");
        const projectId = created?.metadata?.project?.id;
        if (projectId) await renderContextArtifacts(projectId);
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

  function renderWorkType(body) {
    const badge = document.getElementById("work-type-badge");
    if (!badge) return;
    const wt = String(body.work_type || "").trim().toLowerCase();
    if (!wt) {
      badge.hidden = true;
      badge.textContent = "";
      badge.dataset.workType = "";
      return;
    }
    badge.hidden = false;
    badge.dataset.workType = wt;
    badge.textContent = `Work type: ${wt}`;
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
    const promo = fs.tier_promotion?.remaining_gates;
    if (Array.isArray(promo) && promo.length) {
      const promoSpan = document.createElement("span");
      promoSpan.className = "muted";
      promoSpan.dataset.testid = "maker-factory-tier-promotion";
      promoSpan.textContent = ` · Next: ${promo[0]}`;
      chip.appendChild(promoSpan);
    }
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

  function renderGateSummary(body) {
    const mount = document.getElementById("gate-summary-banner");
    if (!mount) return;
    const text = String(body.gate_summary || "").trim();
    if (!text) {
      mount.hidden = true;
      mount.textContent = "";
      return;
    }
    mount.hidden = false;
    mount.dataset.testid = "maker-gate-summary";
    mount.textContent = text;
    const ribbon = document.getElementById("learnings-ribbon");
    if (ribbon) {
      ribbon.classList.add("learnings-ribbon--prominent");
      ribbon.dataset.testid = "maker-learnings-ribbon-prominent";
    }
  }

  function renderRoleCost(body) {
    const chip = document.getElementById("role-cost-chip");
    if (!chip) return;
    const cost = body.role_cost_summary;
    if (!cost || !cost.token_total) {
      chip.hidden = true;
      chip.textContent = "";
      return;
    }
    chip.hidden = false;
    chip.dataset.testid = "maker-role-cost-chip";
    const tokens = Number(cost.token_total || 0).toLocaleString();
    const latency =
      cost.inference_p95_ms != null ? ` · p95 ${Math.round(cost.inference_p95_ms)}ms` : "";
    const usd =
      cost.estimated_cost_usd != null ? ` · ~$${cost.estimated_cost_usd}` : "";
    chip.textContent = `Run tokens: ${tokens}${latency}${usd}`;
  }

  function renderProgress(body) {
    const summary = document.getElementById("slice-summary");
    const list = document.getElementById("slice-list");
    renderPressure(body);
    renderWorkType(body);
    renderFactoryStatus(body);
    renderContextBudget(body);
    renderGateSummary(body);
    renderRoleCost(body);
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
  wireIntegratorRibbon();
  void renderIntegratorRibbon(id);

  function devEnvRegressionFromTimeline(events) {
    let http = null;
    let ui = null;
    let httpDetail = "";
    let uiDetail = "";
    let uiFlowId = "";
    let uiFailedStep = null;
    let uiFailedLocator = "";
    for (const ev of [...(events || [])].reverse()) {
      if (ev.event_type !== "stage.passed" && ev.event_type !== "stage.started") continue;
      const stage = ev.payload?.stage_name || "";
      const block = ev.metadata?.dev_env;
      if (!stage.startsWith("dev_env.")) continue;
      if (stage.startsWith("dev_env.regression") && http === null) {
        http = stage.endsWith(".passed");
        httpDetail = typeof block?.regression === "string" ? block.regression : block?.detail || "";
      }
      if (stage.startsWith("dev_env.ui_regression") && ui === null) {
        ui = stage.endsWith(".passed");
        uiDetail =
          typeof block?.ui_regression === "string"
            ? block.ui_regression
            : typeof block?.regression === "string"
              ? block.regression
              : block?.detail || "";
        uiFlowId = block?.flow_id || "";
        uiFailedStep = block?.failed_step ?? null;
        uiFailedLocator = block?.locator || "";
      }
      if (http !== null && ui !== null) break;
    }
    return { http, ui, httpDetail, uiDetail, uiFlowId, uiFailedStep, uiFailedLocator };
  }

  async function refreshDevEnvStatus(runId) {
    const body = document.getElementById("dev-env-status-body");
    const detail = document.getElementById("dev-env-regression-detail");
    if (!body) return;
    try {
      const st = await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/status`);
      const active = st.active ? "active" : "inactive";
      body.textContent = `Session ${active}${st.session?.base_url ? ` · ${st.session.base_url}` : ""}`;
      if (detail) {
        const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=80`);
        const reg = devEnvRegressionFromTimeline(timeline.events || []);
        const bits = [];
        if (reg.http !== null) {
          bits.push(`HTTP regression: ${reg.http ? "passed" : "failed"}${reg.httpDetail ? ` (${reg.httpDetail.slice(0, 80)})` : ""}`);
        }
        if (reg.ui !== null) {
          let uiLine = `UI regression: ${reg.ui ? "passed" : "failed"}`;
          if (reg.uiFlowId) uiLine += ` [${reg.uiFlowId}]`;
          if (!reg.ui && reg.uiFailedStep != null) {
            uiLine += ` step ${reg.uiFailedStep}`;
          }
          if (!reg.ui && reg.uiFailedLocator) {
            uiLine += ` ${reg.uiFailedLocator}`;
          }
          if (reg.uiDetail) uiLine += ` (${reg.uiDetail.slice(0, 80)})`;
          bits.push(uiLine);
        }
        detail.textContent = bits.length ? bits.join(" · ") : "No regression runs yet";
      }
    } catch {
      body.textContent = "Dev env status unavailable";
      if (detail) detail.textContent = "";
    }
  }

  async function refreshInterjectionQueue(runId) {
    const body = document.getElementById("interjection-queue-body");
    if (!body) return;
    try {
      const q = await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`);
      const items = q.queue?.items || [];
      body.textContent = items.length
        ? items.map((i) => `[${i.priority}] ${i.message}`).join(" · ")
        : "Queue empty";
    } catch {
      body.textContent = "";
    }
  }

  async function refreshVariantRibbon(runId) {
    const body = document.getElementById("variant-body");
    const list = document.getElementById("variant-list");
    if (!body || !runId) return;
    if (list) list.innerHTML = "";
    try {
      const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=80`);
      for (const ev of [...(timeline.events || [])].reverse()) {
        const arena = ev.metadata?.variant_arena;
        if (!arena) continue;
        const candidates = Array.isArray(arena.candidates) ? arena.candidates : [];
        const winner = arena.winner;
        const bits = [`${candidates.length} candidate(s)`];
        if (winner?.label) bits.push(`winner: ${winner.label} (${winner.fitness ?? "?"})`);
        if (arena.promoted_to_workspace) bits.push("promoted");
        body.textContent = bits.join(" · ");
        if (list) {
          for (const c of candidates) {
            const li = document.createElement("li");
            const label = c.label || c.id || "candidate";
            const fitness = c.fitness ?? "?";
            li.textContent = `${label}: fitness ${fitness}`;
            li.dataset.testid = "maker-variant-candidate";
            list.appendChild(li);
          }
        }
        return;
      }
      body.textContent = "No variant experiments yet";
    } catch {
      body.textContent = "Variant arena unavailable";
    }
  }

  async function refreshCouncilRibbon(runId) {
    const panel = document.getElementById("council-ribbon");
    const body = document.getElementById("council-body");
    if (!panel || !body || !runId) return;
    try {
      const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=50`);
      const events = timeline.events || [];
      const parts = [];
      for (const ev of [...events].reverse()) {
        const meta = ev.metadata || {};
        const imp = meta.improvement_council;
        if (imp?.selected) {
          parts.push(`Improvement: ${imp.selected}`);
          const gaps = imp.feature_gap_matrix?.gaps;
          if (Array.isArray(gaps) && gaps.length) {
            parts.push(`Gaps: ${gaps.join(", ")}`);
          }
          break;
        }
      }
      for (const ev of [...events].reverse()) {
        const meta = ev.metadata || {};
        const res = meta.resolution_council;
        if (res?.detail) {
          parts.push(`Resolution: ${res.detail}${res.accord ? " (accord)" : ""}`);
          break;
        }
      }
      if (!parts.length) {
        panel.hidden = true;
        body.textContent = "";
        return;
      }
      panel.hidden = false;
      body.textContent = parts.join(" · ");
    } catch {
      panel.hidden = true;
    }
  }

  function renderAutopilotCheckpoints(selected) {
    const mount = document.getElementById("autopilot-checkpoints");
    if (!mount) return;
    mount.replaceChildren();
    const selectedSet = new Set(selected || []);
    AUTOPILOT_CHECKPOINT_CATALOG.forEach((id) => {
      const label = document.createElement("label");
      label.className = "autopilot-checkpoint";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.value = id;
      box.dataset.testid = `maker-autopilot-cp-${id}`;
      box.checked = selectedSet.has(id);
      label.appendChild(box);
      label.append(` ${id.replaceAll("_", " ")}`);
      mount.appendChild(label);
    });
  }

  function selectedAutopilotCheckpoints() {
    return [...document.querySelectorAll("#autopilot-checkpoints input[type=checkbox]:checked")]
      .map((el) => el.value)
      .filter(Boolean);
  }

  async function refreshLearningsPanel(runId) {
    const list = document.getElementById("learnings-list");
    const stitchBanner = document.getElementById("stitch-suggestion");
    if (!list) return;
    try {
      const body = await apiJson(`/runs/${encodeURIComponent(runId)}/learnings`);
      const items = body.learnings || [];
      if (stitchBanner) {
        const sug = body.stitch_suggestion;
        if (sug?.candidate_id) {
          stitchBanner.hidden = false;
          stitchBanner.textContent = `Repeated failure (${sug.fingerprint || "fingerprint"}) — consider stitch candidate ${sug.candidate_id}`;
        } else {
          stitchBanner.hidden = true;
          stitchBanner.textContent = "";
        }
      }
      list.replaceChildren();
      if (!items.length) {
        const empty = document.createElement("li");
        empty.className = "muted";
        empty.textContent = "No learnings yet";
        list.appendChild(empty);
        return;
      }
      items.forEach((item) => {
        const li = document.createElement("li");
        li.dataset.testid = `maker-learning-${item.learning_id || "item"}`;
        li.textContent = item.title || item.learning_id || "Learning";
        if (item.excerpt) li.title = item.excerpt;
        list.appendChild(li);
      });
    } catch {
      list.replaceChildren();
      const err = document.createElement("li");
      err.className = "muted";
      err.textContent = "Learnings unavailable";
      list.appendChild(err);
    }
  }

  async function loadAutopilotProfiles() {
    const select = document.getElementById("autopilot-profile-select");
    if (!select) return;
    try {
      const body = await apiJson("/platform/autopilot/user-profiles");
      const profiles = body.profiles || [];
      select.replaceChildren();
      const custom = document.createElement("option");
      custom.value = "";
      custom.textContent = "— custom —";
      select.appendChild(custom);
      profiles.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.profile_id;
        opt.textContent = p.name || p.profile_id;
        select.appendChild(opt);
      });
    } catch {
      /* optional */
    }
  }

  function applyAutopilotProfile(profileId, profiles) {
    const match = (profiles || []).find((p) => p.profile_id === profileId);
    if (!match) return;
    const slider = document.getElementById("autopilot-slider");
    const label = document.getElementById("autopilot-level-label");
    if (slider) slider.value = String(match.level ?? 5);
    if (label) label.textContent = String(match.level ?? 5);
    renderAutopilotCheckpoints(match.checkpoints || []);
  }

  function wireOperatorRibbons(runId) {
    document.getElementById("dev-env-start-btn")?.addEventListener("click", async () => {
      try {
        await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/start`, { method: "POST" });
        toast("Dev env started", "success");
        await refreshDevEnvStatus(runId);
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
    document.getElementById("dev-env-stop-btn")?.addEventListener("click", async () => {
      try {
        await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/stop`, { method: "POST" });
        toast("Dev env stopped", "success");
        await refreshDevEnvStatus(runId);
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
    document.getElementById("dev-env-regression-btn")?.addEventListener("click", async () => {
      try {
        const res = await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/regression`, {
          method: "POST",
        });
        toast(res.passed ? "Regression passed" : `Regression failed: ${res.detail}`, res.passed ? "success" : "error");
        await refreshDevEnvStatus(runId);
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
    const postInterjection = async (priority) => {
      const msg = document.getElementById("interjection-message")?.value?.trim();
      if (!msg) return toast("Enter a message", "error");
      try {
        await apiJson(`/runs/${encodeURIComponent(runId)}/interjection-queue`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg, priority }),
        });
        toast("Queued", "success");
        document.getElementById("interjection-message").value = "";
        await refreshInterjectionQueue(runId);
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    };
    document.getElementById("interjection-next-btn")?.addEventListener("click", () => postInterjection("next"));
    document.getElementById("interjection-last-btn")?.addEventListener("click", () => postInterjection("last"));
    const slider = document.getElementById("autopilot-slider");
    const label = document.getElementById("autopilot-level-label");
    slider?.addEventListener("input", () => {
      if (label) label.textContent = String(slider.value);
    });
    document.getElementById("autopilot-save-btn")?.addEventListener("click", async () => {
      const level = Number(slider?.value || 5);
      const checkpoints = selectedAutopilotCheckpoints();
      try {
        await apiJson(`/runs/${encodeURIComponent(runId)}/autopilot`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ level, checkpoints }),
        });
        toast(`Autopilot level ${level} applied`, "success");
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
    document.getElementById("autopilot-profile-save-btn")?.addEventListener("click", async () => {
      const level = Number(slider?.value || 5);
      const checkpoints = selectedAutopilotCheckpoints();
      const profileId = window.prompt("Profile id (slug)", "default")?.trim();
      if (!profileId) return;
      const name = window.prompt("Display name", profileId)?.trim() || profileId;
      try {
        await apiJson(`/platform/autopilot/user-profiles/${encodeURIComponent(profileId)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, level, checkpoints }),
        });
        toast(`Saved profile ${profileId}`, "success");
        await loadAutopilotProfiles();
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
    document.getElementById("autopilot-profile-select")?.addEventListener("change", async (ev) => {
      const pid = ev.target?.value;
      if (!pid) return;
      try {
        const body = await apiJson("/platform/autopilot/user-profiles");
        applyAutopilotProfile(pid, body.profiles || []);
      } catch {
        /* ignore */
      }
    });
    void refreshDevEnvStatus(runId);
    void refreshInterjectionQueue(runId);
    void refreshCouncilRibbon(runId);
    void refreshVariantRibbon(runId);
    void refreshLearningsPanel(runId);
    void loadAutopilotProfiles();
    apiJson(`/runs/${encodeURIComponent(runId)}/autopilot`)
      .then((ap) => {
        const level = ap.level ?? 5;
        if (slider) slider.value = String(level);
        if (label) label.textContent = String(level);
        renderAutopilotCheckpoints(ap.checkpoints || []);
        const compactPick = document.getElementById("theater-compact-pick-btn");
        if (compactPick) compactPick.hidden = level >= 9;
        const checkpointsMount = document.getElementById("autopilot-checkpoints");
        if (checkpointsMount) checkpointsMount.hidden = level >= 9;
      })
      .catch(() => renderAutopilotCheckpoints([]));
  }

  wireOperatorRibbons(id);

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
    const rid = resolveRunId();
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
        li.className = "context-artifact-row";
        li.dataset.testid = "maker-context-artifact";
        const label = document.createElement("span");
        label.textContent = `${art.title || art.artifact_id} (${art.kind || "note"})`;
        label.title = String(art.content || "").slice(0, 400);
        li.appendChild(label);
        if (rid) {
          const insertBtn = document.createElement("button");
          insertBtn.type = "button";
          insertBtn.textContent = "Insert into run";
          insertBtn.dataset.testid = "maker-context-artifact-insert";
          insertBtn.addEventListener("click", async () => {
            try {
              await apiJson(
                `/runs/${encodeURIComponent(rid)}/context-artifacts/${encodeURIComponent(art.artifact_id)}/insert`,
                { method: "POST" },
              );
              toast("Artifact inserted into run context", "success");
            } catch (e) {
              toast(String(e.message || e), "error");
            }
          });
          li.appendChild(insertBtn);
        }
        list.appendChild(li);
      }
    } catch {
      list.replaceChildren();
    }
  }

  async function renderIntegratorRibbon(runId) {
    const panel = document.getElementById("integrator-ribbon");
    const bodyEl = document.getElementById("integrator-ribbon-body");
    if (!panel || !bodyEl || !runId) return;
    try {
      const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=1`);
      const ig = timeline.integrator_gate;
      const delta = timeline.integrator_gate_delta;
      const parts = [];
      if (ig && ig.verdict) {
        parts.push(`Integrator gate: ${ig.verdict}`);
      }
      if (delta && delta.summary) {
        parts.push(String(delta.summary));
      }
      if (!parts.length) {
        bodyEl.textContent = "No integrator gate summary yet.";
        return;
      }
      bodyEl.textContent = parts.join(" · ");
    } catch {
      bodyEl.textContent = "Integrator summary unavailable.";
    }
  }

  let stitchCatalogVersion = 1;
  async function refreshStitchFromProgress() {
    try {
      const catalogBody = await apiJson("/bundles/catalog").catch(() => ({ document_version: 1 }));
      stitchCatalogVersion = catalogBody.document_version ?? 1;
      const candBody = await apiJson("/bundles/catalog-candidates?limit=20");
      const pending = (candBody.candidates || []).filter((c) => (c.status || "pending") === "pending");
      const bodyEl = document.getElementById("integrator-ribbon-body");
      if (bodyEl && pending.length) {
        bodyEl.textContent = `${bodyEl.textContent ? bodyEl.textContent + " · " : ""}${pending.length} stitch candidate(s) pending`;
      }
    } catch {
    }
  }

  function wireIntegratorRibbon() {
    document.getElementById("integrator-stitch-refresh")?.addEventListener("click", () => {
      refreshStitchFromProgress().catch((e) => toast(String(e.message || e), "error"));
    });
    document.getElementById("integrator-stitch-promote-batch")?.addEventListener("click", async () => {
      try {
        await apiJson(
          `/bundles/catalog-candidates/promote-stitch-pending?expected_version=${stitchCatalogVersion}`,
          { method: "POST" },
        );
        toast("Stitch batch promote complete", "success");
        await refreshStitchFromProgress();
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
  }

  try {
    const timeline = await apiJson(`/runs/${id}/timeline?limit=1`);
    const created = (timeline.events || []).find((e) => e.event_type === "run.created");
    const projectId = created?.metadata?.project?.id;
    if (projectId) await renderContextArtifacts(projectId);
  } catch {
  }

  try {
    const mem = await apiJson(`/runs/${id}/memory-influence`);
    const tbody = document.querySelector("#memory-influence-table tbody");
    if (tbody) {
      tbody.replaceChildren();
      for (const row of mem.rows || []) {
        const tr = document.createElement("tr");
        tr.dataset.testid = "maker-memory-influence-row";
        tr.innerHTML = `<td>${row.stage || ""}</td><td>${row.hits || ""}</td><td>${row.query_digest || ""}</td>`;
        tbody.appendChild(tr);
      }
    }
  } catch {
  }
}

export function unmountProgress() {
  window.dispatchEvent(new Event("maker-route-leave-progress"));
}
