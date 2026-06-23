import { apiJson } from "../../api-client.js";

export function devEnvRegressionFromTimeline(events) {
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

export async function refreshDevEnvStatus(runId) {
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
        if (!reg.ui && reg.uiFailedStep != null) uiLine += ` step ${reg.uiFailedStep}`;
        if (!reg.ui && reg.uiFailedLocator) uiLine += ` ${reg.uiFailedLocator}`;
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

export async function refreshVariantRibbon(runId) {
  const body = document.getElementById("variant-body");
  const list = document.getElementById("variant-list");
  if (!body || !runId) return;
  if (list) list.innerHTML = "";
  try {
    const [timeline, progress] = await Promise.all([
      apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=80`),
      apiJson(`/runs/${encodeURIComponent(runId)}/maker-progress?simple=true`).catch(() => null),
    ]);
    for (const ev of [...(timeline.events || [])].reverse()) {
      const arena = ev.metadata?.variant_arena;
      if (!arena) continue;
      const candidates = Array.isArray(arena.candidates) ? arena.candidates : [];
      const winner = arena.winner;
      const bits = [`${candidates.length} candidate(s)`];
      if (winner?.label) bits.push(`winner: ${winner.label} (${winner.fitness ?? "?"})`);
      if (arena.promoted_to_workspace) bits.push("promoted");
      if (arena.crossover_merged) bits.push("crossover merged");
      let explore = progress?.repo_explore;
      if (!explore) {
        for (const row of timeline.events || []) {
          if (row.metadata?.repo_explore) {
            explore = row.metadata.repo_explore;
            break;
          }
        }
      }
      if (explore) {
        const findings = Array.isArray(explore.findings) ? explore.findings.length : 0;
        const nodes = explore.graph?.nodes?.length;
        if (findings) bits.push(`${findings} exploration finding(s)`);
        else if (nodes) bits.push(`${nodes} graph node(s)`);
      }
      body.textContent = bits.join(" · ");
      if (list) {
        for (const c of candidates) {
          const li = document.createElement("li");
          li.textContent = `${c.label || c.id || "candidate"}: fitness ${c.fitness ?? "?"}`;
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

export async function refreshCouncilRibbon(runId) {
  const panel = document.getElementById("council-ribbon");
  const body = document.getElementById("council-body");
  if (!panel || !body || !runId) return;
  try {
    const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=50`);
    const events = timeline.events || [];
    const parts = [];
    for (const ev of [...events].reverse()) {
      const imp = ev.metadata?.improvement_council;
      if (imp?.selected) {
        parts.push(`Improvement: ${imp.selected}`);
        const gaps = imp.feature_gap_matrix?.gaps;
        if (Array.isArray(gaps) && gaps.length) parts.push(`Gaps: ${gaps.join(", ")}`);
        break;
      }
    }
    for (const ev of [...events].reverse()) {
      const res = ev.metadata?.resolution_council;
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

export async function refreshLearningsPanel(runId) {
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
