import { formatGateSummary } from "../../gate-summary.js";
import { formatPlainGateSummary } from "../../plain-language.js";

const BLOCKING_SEVERITIES = new Set(["BLOCKER", "HIGH"]);

function reproSummary(steps) {
  if (!Array.isArray(steps) || !steps.length) return "";
  const joined = steps.map((s) => String(s).trim()).filter(Boolean).join(" → ");
  return joined.length > 160 ? `${joined.slice(0, 157)}…` : joined;
}

export function findingsShowAll() {
  const box = document.getElementById("findings-show-all");
  return Boolean(box?.checked);
}

export function renderFindings(findings, { showAll = findingsShowAll() } = {}) {
  const list = document.getElementById("findings-list");
  const countEl = document.getElementById("findings-count");
  if (!list) return;
  list.replaceChildren();
  const all = findings || [];
  const blocked = all.filter((ev) => {
    const sev = String(ev?.payload?.severity || "").toUpperCase();
    return BLOCKING_SEVERITIES.has(sev);
  });
  if (countEl) {
    if (all.length) {
      countEl.hidden = false;
      countEl.textContent = showAll
        ? `${all.length} finding(s)`
        : `${blocked.length} blocking · ${all.length} total`;
    } else {
      countEl.hidden = true;
      countEl.textContent = "";
    }
  }
  const items = showAll ? all : blocked.length ? blocked : all;
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
    li.className = `finding-card severity-${sev.toLowerCase()}${BLOCKING_SEVERITIES.has(sev) ? "" : " finding-card--advisory"}`;
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
    const summary = pl.summary || pl.message || pl.headline;
    if (summary) {
      const detail = document.createElement("p");
      detail.className = "finding-summary";
      detail.dataset.testid = "maker-finding-summary";
      detail.textContent = String(summary);
      li.appendChild(detail);
    }
    if (pl.evidence || pl.body_md) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "linkish";
      toggle.textContent = "Evidence";
      const pre = document.createElement("pre");
      pre.className = "finding-evidence";
      pre.hidden = true;
      pre.textContent = String(pl.evidence || pl.body_md || "");
      toggle.addEventListener("click", () => {
        pre.hidden = !pre.hidden;
        toggle.textContent = pre.hidden ? "Evidence" : "Hide";
      });
      li.appendChild(toggle);
      li.appendChild(pre);
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

export function renderGateSummaryBanner(body) {
  const mount = document.getElementById("gate-summary-banner");
  if (!mount) return;
  const text = formatPlainGateSummary(body.gate_summary) || formatGateSummary(body.gate_summary);
  if (!text) {
    mount.hidden = true;
    mount.textContent = "";
    return;
  }
  mount.hidden = false;
  mount.dataset.testid = "maker-gate-summary";
  mount.textContent = text;
  const workspace = document.getElementById("findings-workspace");
  if (workspace) workspace.dataset.gateFailed = "1";
  const ribbon = document.getElementById("learnings-ribbon");
  if (ribbon) {
    ribbon.classList.add("learnings-ribbon--prominent");
    ribbon.dataset.testid = "maker-learnings-ribbon-prominent";
  }
}

export async function renderGateFailSteps(apiJson, runId) {
  const mount = document.getElementById("gate-fail-steps");
  if (!mount || !runId) return;
  try {
    const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline`);
    const failed = [];
    for (const ev of timeline.events || []) {
      const stage = String(ev.payload?.stage_name || "");
      if (stage === "slice.gate") {
        const verdict = String(ev.metadata?.slice_gate_verdict || "").toUpperCase();
        if (verdict !== "FAIL") continue;
        const steps = ev.metadata?.slice_gate_steps || ev.metadata?.gate_steps;
        failed.push({ seq: ev.store_seq, steps, detail: ev.metadata?.slice_gate_detail });
        continue;
      }
      if (stage === "enforcement.gate" && String(ev.event_type || "") === "stage.failed") {
        failed.push({
          seq: ev.store_seq,
          steps: ev.metadata?.enforcement_steps,
          detail: ev.payload?.message || ev.metadata?.enforcement_detail,
        });
      }
    }
    mount.replaceChildren();
    if (!failed.length) {
      mount.hidden = true;
      return;
    }
    mount.hidden = false;
    const title = document.createElement("h4");
    title.textContent = "Failed gate steps";
    title.dataset.testid = "maker-gate-fail-steps-title";
    mount.appendChild(title);
    const ul = document.createElement("ul");
    ul.dataset.testid = "maker-gate-fail-steps-list";
    for (const item of failed.slice(-3)) {
      const li = document.createElement("li");
      li.className = "gate-fail-step";
      const stepText = Array.isArray(item.steps)
        ? item.steps.map((s) => (typeof s === "object" ? s.name || s.step : s)).join(" → ")
        : item.detail || `seq ${item.seq}`;
      li.textContent = stepText || "Gate FAIL";
      ul.appendChild(li);
    }
    mount.appendChild(ul);
  } catch {
    mount.hidden = true;
  }
}
