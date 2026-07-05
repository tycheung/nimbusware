import { toast, apiJson } from "../../api-client.js";
import { plainSurfaceLabel } from "../../plain-language.js";
import { formatGateSummary } from "../../gate-summary.js";
import { ARCHETYPE_SUBCHOICE_STORAGE_KEY } from "../../operator-default-profiles.js";
import { resolveRunId } from "../../session-hub.js";
import { renderGateSummaryBanner, renderGateFailSteps } from "./findings-gates.js";
import {
  renderEnforcementStatus,
  renderFactoryStatus,
  renderStandardsStatus,
  renderWorkType,
} from "./progress_status_chips.js";

export {
  renderWorkType,
  renderEnforcementStatus,
  renderStandardsStatus,
  renderFactoryStatus,
} from "./progress_status_chips.js";

export function renderCompactionPreview(last) {
  const panel = document.getElementById("compaction-preview");
  const meta = document.getElementById("compaction-preview-meta");
  const summary = document.getElementById("compaction-preview-summary");
  const toggle = document.getElementById("compaction-preview-toggle");
  if (!panel || !meta) return;
  if (!last?.compaction_id) {
    panel.hidden = true;
    meta.textContent = "";
    if (summary) {
      summary.hidden = true;
      summary.textContent = "";
    }
    return;
  }
  panel.hidden = false;
  const parts = [
    last.trigger ? `trigger: ${last.trigger}` : "",
    last.tokens_before != null && last.tokens_after != null
      ? `${last.tokens_before}→${last.tokens_after} tokens`
      : "",
    last.merged_handoff_count != null ? `${last.merged_handoff_count} handoffs merged` : "",
    last.compaction_id ? `id ${String(last.compaction_id).slice(0, 8)}…` : "",
  ].filter(Boolean);
  meta.textContent = parts.join(" · ") || "Compaction recorded";
  if (summary && toggle) {
    const text = String(last.summary || "").trim();
    summary.textContent = text;
    summary.hidden = true;
    toggle.hidden = !text;
    toggle.textContent = "Show summary";
    toggle.onclick = () => {
      summary.hidden = !summary.hidden;
      toggle.textContent = summary.hidden ? "Show summary" : "Hide summary";
    };
  }
}

export function renderContextBudget(body) {
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
  const samples = budget.token_samples || {};
  const sampleParts = [];
  if (samples.tokens_in) sampleParts.push(`in ${samples.tokens_in}`);
  if (samples.tokens_out) sampleParts.push(`out ${samples.tokens_out}`);
  if (samples.cache_read) sampleParts.push(`cache hit ${samples.cache_read}`);
  if (samples.cache_write) sampleParts.push(`cache write ${samples.cache_write}`);
  const sampleHint = sampleParts.length ? ` · LLM ${sampleParts.join(", ")}` : "";
  const savings = budget.token_savings || {};
  const savingsHint =
    savings.offload_saved > 0 ? ` · offload saved ${savings.offload_saved} tok` : "";
  chip.textContent = `Context ${pct}% (${budget.estimated_tokens}/${budget.window_tokens} tok)${compactHint}${sampleHint}${savingsHint}`;
  chip.title =
    "Advisory planner context vs model window; LLM totals from persisted budget samples when available";
  chip.dataset.testid = "maker-context-budget-chip";
  renderCompactionPreview(last);
}

export function renderPressure(body) {
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

export function renderRoleCost(body) {
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
  const latency = cost.inference_p95_ms != null ? ` · p95 ${Math.round(cost.inference_p95_ms)}ms` : "";
  const usd = cost.estimated_cost_usd != null ? ` · ~$${cost.estimated_cost_usd}` : "";
  chip.textContent = `Run tokens: ${tokens}${latency}${usd}`;
}

function bodyRunStatus(completionPayload) {
  if (!completionPayload) return "";
  const verdict = String(completionPayload.verdict || "").toUpperCase();
  if (verdict === "PASS") return "completed";
  if (verdict === "FAIL") return "failed";
  return "";
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

export function renderCampaignControls(cp) {
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

function isSafeCodingArchetype() {
  return localStorage.getItem(ARCHETYPE_SUBCHOICE_STORAGE_KEY) === "safe_coding";
}

function completionHeadline(state, cp, completionPayload, gateSummary) {
  const verdict = String(completionPayload?.verdict || "").toUpperCase();
  const slices =
    cp?.slices_total != null ? ` · ${cp.slices_completed || 0}/${cp.slices_total} slices` : "";
  if (verdict === "PASS" || state === "completed") {
    if (isSafeCodingArchetype()) {
      return `Your app passed automated checks — review the summary before sharing${slices}`;
    }
    return `Campaign complete — launch-ready${slices}`;
  }
  if (verdict === "FAIL" || state === "failed") {
    if (isSafeCodingArchetype()) {
      return `Build finished with issues — check gates and tests before retrying${slices}`;
    }
    return `Campaign finished — needs attention${slices}`;
  }
  if (gateSummary && (state === "completed" || state === "failed")) {
    const gateText = formatGateSummary(gateSummary);
    if (gateText) return `Campaign ${state} — ${gateText}${slices}`;
  }
  return `Campaign: ${state}${slices}`;
}

export function renderCompletion(completionPayload, cp, body = {}) {
  const panel = document.getElementById("completion-cockpit");
  if (!panel) return;
  const runStatus = String(body.run_status || "").toLowerCase();
  const gateSummary = body.gate_summary;
  const cpState = String(cp?.state || "").toLowerCase();
  const isTerminal =
    runStatus === "completed" ||
    runStatus === "failed" ||
    cpState === "completed" ||
    cpState === "failed";
  const show =
    Boolean(cp?.state) || Boolean(completionPayload) || isTerminal || Boolean(gateSummary);
  panel.hidden = !show;
  if (!show) return;

  const terminalEl = document.getElementById("completion-terminal");
  const rationale = document.getElementById("completion-rationale");
  const blocking = document.getElementById("completion-blocking");
  const latest = completionPayload || {};
  const verdict = String(latest.verdict || "").toUpperCase();
  const state = String(cp?.state || bodyRunStatus(completionPayload) || runStatus || "executing");
  if (terminalEl) {
    terminalEl.textContent = completionHeadline(state, cp, latest, gateSummary);
    terminalEl.dataset.state = state;
    terminalEl.dataset.testid = "maker-completion-terminal";
    terminalEl.classList.toggle("completion-terminal--ready", verdict === "PASS" || state === "completed");
    terminalEl.classList.toggle("completion-terminal--failed", verdict === "FAIL" || state === "failed");
  }
  if (rationale) {
    const gateText = formatGateSummary(gateSummary);
    const rationaleText = latest.rationale || (gateText ? `Gate: ${gateText}` : "");
    rationale.textContent = rationaleText;
    rationale.hidden = !rationaleText;
  }
  if (blocking) {
    blocking.replaceChildren();
    const findings = latest.blocking_findings || [];
    if (!findings.length) {
      const li = document.createElement("li");
      li.className = "muted";
      if (latest.verdict) {
        li.textContent = `Verdict: ${latest.verdict}`;
      } else if (isTerminal && gateSummary) {
        li.textContent = `Launch readiness: ${formatGateSummary(gateSummary) || "see gate summary above"}`;
        li.dataset.testid = "maker-completion-launch-hint";
      } else {
        li.textContent = "No blocking findings recorded.";
      }
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

export async function loadCompletionEval(runId) {
  try {
    const body = await apiJson(`/campaigns/${encodeURIComponent(runId)}/progress`);
    const evals = body.completion_evaluations || [];
    return evals.length ? evals[evals.length - 1] : null;
  } catch {
    return null;
  }
}

export function renderProgressBody(body) {
  const summary = document.getElementById("slice-summary");
  const list = document.getElementById("slice-list");
  renderPressure(body);
  renderWorkType(body);
  renderEnforcementStatus(body);
  renderStandardsStatus(body);
  renderFactoryStatus(body);
  renderContextBudget(body);
  renderGateSummaryBanner(body);
  renderRoleCost(body);
  if (body.gate_summary) {
    const rid = resolveRunId();
    if (rid) void renderGateFailSteps(apiJson, rid);
  }
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
      const surface = s.surface_id ? `${plainSurfaceLabel(s.surface_id)} · ` : "";
      li.textContent = `${surface}${s.headline || s.slice_id} — ${s.status || s.state || ""}`;
      list.appendChild(li);
    }
  }
  const handoffMount = document.getElementById("handoff-preview");
  const handoff = body.latest_handoff;
  if (handoffMount) {
    if (handoff && handoff.summary) {
      handoffMount.hidden = false;
      handoffMount.textContent = `Latest handoff: ${String(handoff.summary).slice(0, 200)}`;
      handoffMount.dataset.testid = "maker-latest-handoff";
    } else {
      handoffMount.hidden = true;
      handoffMount.textContent = "";
    }
  }
  if (body._completion_eval != null || body.campaign_progress || body.gate_summary) {
    renderCompletion(body._completion_eval, body.campaign_progress, body);
  }
}
