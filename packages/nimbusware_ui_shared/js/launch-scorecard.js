const SCORECARD_DIMENSIONS = [
  ["aggregate", "aggregate"],
  ["maturity", "maturity"],
  ["maintainability", "maintainability"],
  ["scalability", "scalability"],
  ["security", "security"],
  ["testability", "testability"],
];

const DEV_ENV_ROWS = [
  ["dev_env live regression", "dev_env_live_regression_passed"],
  ["dev_env HTTP regression", "dev_env_http_regression_passed"],
  ["dev_env UI regression", "dev_env_ui_regression_passed"],
  ["slice E2E", "slice_e2e_passed"],
];

/**
 * @param {{ events?: Array<Record<string, unknown>> } | null} timeline
 */
export function scorecardFromTimeline(timeline) {
  const events = timeline?.events || [];
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (ev.event_type !== "stage.passed") continue;
    const payload = ev.payload || {};
    if (payload.stage_name !== "launch_eval.completed") continue;
    return ev.metadata || payload;
  }
  return null;
}

export async function fetchScorecardForRun(apiJson, runId) {
  const timeline = await apiJson(`/runs/${runId}/timeline`);
  return scorecardFromTimeline(timeline);
}

export function renderLaunchScorecard(container, scorecard, { testIdPrefix = "launch", tableClass = "scorecard-table" } = {}) {
  if (!container || !scorecard) return;
  container.replaceChildren();
  const table = document.createElement("table");
  table.className = tableClass;
  table.dataset.testid = `${testIdPrefix}-scorecard-table`;
  const tbody = document.createElement("tbody");
  for (const [label, key] of SCORECARD_DIMENSIONS) {
    const value = scorecard[key];
    if (value == null) continue;
    const tr = document.createElement("tr");
    tr.dataset.testid = `${testIdPrefix}-scorecard-${label}`;
    tr.innerHTML = `<th scope="row">${label}</th><td>${value}</td>`;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  container.appendChild(table);
  if (scorecard.passed != null) {
    const status = document.createElement("p");
    status.textContent = scorecard.passed ? "passed" : "needs work";
    status.dataset.testid = `${testIdPrefix}-scorecard-status`;
    container.appendChild(status);
  }
  for (const [label, key] of DEV_ENV_ROWS) {
    if (scorecard[key] == null) continue;
    const row = document.createElement("p");
    row.dataset.testid = `${testIdPrefix}-scorecard-${key}`;
    row.textContent = `${label}: ${scorecard[key] ? "passed" : "failed"}`;
    container.appendChild(row);
  }
  if (scorecard.put_ui_flow_id) {
    const flowRow = document.createElement("p");
    flowRow.dataset.testid = `${testIdPrefix}-scorecard-put_ui_flow_id`;
    flowRow.textContent = `UI flow: ${scorecard.put_ui_flow_id}`;
    container.appendChild(flowRow);
  }
  if (scorecard.dev_env_ui_failed_step != null || scorecard.dev_env_ui_failed_locator) {
    const failRow = document.createElement("p");
    failRow.dataset.testid = `${testIdPrefix}-scorecard-ui-flow-failure`;
    const parts = [];
    if (scorecard.dev_env_ui_failed_step != null) {
      parts.push(`step ${scorecard.dev_env_ui_failed_step}`);
    }
    if (scorecard.dev_env_ui_failed_locator) {
      parts.push(scorecard.dev_env_ui_failed_locator);
    }
    failRow.textContent = `UI flow failure: ${parts.join(" · ")}`;
    container.appendChild(failRow);
  }
  const llmDims = scorecard.llm_dimensions;
  if (llmDims && typeof llmDims === "object" && Object.keys(llmDims).length) {
    const heading = document.createElement("h4");
    heading.textContent = "LLM dimensions";
    container.appendChild(heading);
    const llmTable = document.createElement("table");
    llmTable.className = tableClass;
    llmTable.dataset.testid = `${testIdPrefix}-llm-dimensions`;
    const llmBody = document.createElement("tbody");
    for (const [key, val] of Object.entries(llmDims)) {
      const tr = document.createElement("tr");
      tr.dataset.testid = `${testIdPrefix}-llm-dimension-${key}`;
      tr.innerHTML = `<th scope="row">${key}</th><td>${val}</td>`;
      llmBody.appendChild(tr);
    }
    llmTable.appendChild(llmBody);
    container.appendChild(llmTable);
  }
  const findings = scorecard.findings || scorecard.llm_findings;
  if (Array.isArray(findings) && findings.length) {
    const heading = document.createElement("h4");
    heading.textContent = "Findings";
    container.appendChild(heading);
    const ul = document.createElement("ul");
    ul.dataset.testid = `${testIdPrefix}-scorecard-findings`;
    for (const item of findings.slice(0, 8)) {
      const li = document.createElement("li");
      li.textContent = String(item);
      ul.appendChild(li);
    }
    container.appendChild(ul);
  }
}
