/** Render critic reliability table (Maker port of Admin CriticReliabilityPanel). */

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
