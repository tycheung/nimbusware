export function renderCriticReliabilityPanel(container, body, { testIdPrefix = "maker-critic" } = {}) {
  container.replaceChildren();
  const caption = document.createElement("p");
  caption.className = "muted";
  caption.dataset.testid = `${testIdPrefix}-caption`;
  caption.textContent = body?.caption || "No critic reliability data.";
  container.appendChild(caption);

  const rows = body?.rows || [];
  if (!rows.length) return;

  const table = document.createElement("table");
  table.className = "data-table";
  table.dataset.testid = `${testIdPrefix}-table`;
  const thead = document.createElement("thead");
  thead.innerHTML = "<tr><th>Metric</th><th>Value</th></tr>";
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.testid = `${testIdPrefix}-row`;
    tr.innerHTML = `<td>${row.metric || ""}</td><td>${row.value || ""}</td>`;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  container.appendChild(table);
}

export async function loadRunCriticReliability(apiJson, runId) {
  return apiJson(`/runs/${encodeURIComponent(runId)}/critic-reliability`);
}

export async function loadFleetCriticReliability(apiJson) {
  try {
    const body = await apiJson("/platform/analytics/competitive-summary?limit_runs=200");
    const snap = body?.metrics?.critic_reliability;
    if (!snap || typeof snap !== "object") {
      return { caption: "No fleet critic snapshot.", rows: [] };
    }
    const rows = [];
    if (snap.critic_fail_rate != null) {
      const rate = Number(snap.critic_fail_rate);
      rows.push({
        metric: "Critic FAIL rate (fleet)",
        value: Number.isFinite(rate) ? `${(rate * 100).toFixed(1)}%` : String(snap.critic_fail_rate),
      });
    }
    if (snap.runs_scanned != null) {
      rows.push({ metric: "Runs scanned", value: String(snap.runs_scanned) });
    }
    if (snap.runs_with_critics != null) {
      rows.push({ metric: "Runs with critics", value: String(snap.runs_with_critics) });
    }
    return {
      caption: snap.note || "Fleet critic reliability snapshot.",
      rows,
    };
  } catch {
    return { caption: "Critic reliability unavailable.", rows: [] };
  }
}

export async function loadRunOrFleetCriticReliability(apiJson, runId) {
  const runBody = await loadRunCriticReliability(apiJson, runId);
  if ((runBody.rows || []).length) return runBody;
  const fleet = await loadFleetCriticReliability(apiJson);
  if (!(fleet.rows || []).length) return runBody;
  return {
    ...fleet,
    caption: `This run has no critic events. ${fleet.caption}`,
  };
}
