import { apiJson, toast } from "../../api-client.js";
import { resolveRunId } from "../../session-hub.js";

export async function renderContextArtifacts(projectId) {
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

export async function renderMemoryInfluence(runId) {
  try {
    const mem = await apiJson(`/runs/${runId}/memory-influence`);
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
    /* ignore */
  }
}
