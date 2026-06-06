import { apiJson } from "../api-client.js";

function runIdFromLocation() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  return params.get("run_id") || document.getElementById("run-theater-run-id")?.value || "";
}

function renderTree(root, tree) {
  const epics = tree.epics || [];
  if (!epics.length) {
    root.innerHTML = "<p class='muted'>No backlog yet — start a campaign from Build.</p>";
    return;
  }
  const parts = ["<div class='plan-tree'>"];
  for (const epic of epics) {
    parts.push(`<details open><summary><strong>${epic.title}</strong> (${epic.status})</summary>`);
    for (const feature of epic.features || []) {
      parts.push(`<div class='plan-feature'><em>${feature.title}</em><ul>`);
      for (const slice of feature.slices || []) {
        parts.push(
          `<li><span class="slice-status">${slice.status}</span> ${slice.slice_id} — ${(slice.rationale || "").slice(0, 80)}</li>`,
        );
      }
      parts.push("</ul></div>");
    }
    parts.push("</details>");
  }
  parts.push("</div>");
  root.innerHTML = parts.join("");
}

export async function mountPlan(root) {
  root.innerHTML = "<p class='muted'>Loading backlog…</p>";
  const runId = runIdFromLocation();
  if (!runId) {
    root.innerHTML = "<p class='muted'>Open a run from Progress or Review to view the plan.</p>";
    return;
  }
  try {
    const tree = await apiJson(`/campaigns/${runId}/backlog`);
    renderTree(root, tree);
  } catch (err) {
    root.innerHTML = `<p class='muted'>Backlog not available yet (${err.message || "pending"}).</p>`;
  }
}
