import { apiJson, toast } from "../../api-client.js";
import { formatDomainMissMessage, isDomainPeelMiss, toastIfMiss } from "../../broker_miss.js"; // sak499-b
import { resolveRunId } from "../../session-hub.js";

export async function renderContextArtifacts(projectId) {
  const list = document.getElementById("context-artifacts-list");
  if (!list || !projectId) return;
  const rid = resolveRunId();
  try {
    const body = await apiJson(`/projects/${encodeURIComponent(projectId)}/context-artifacts`);
    list.replaceChildren();
    if (isDomainPeelMiss(body)) {
      const li = document.createElement("li");
      li.className = "context-artifact-miss";
      li.dataset.testid = "maker-context-artifact-miss";
      li.textContent =
        formatDomainMissMessage(body, "Context artifacts unavailable") || "Context artifacts unavailable";
      list.appendChild(li);
      toastIfMiss(body, toast, "Context artifacts unavailable");
      return;
    }
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
            const result = await apiJson(
              `/runs/${encodeURIComponent(rid)}/context-artifacts/${encodeURIComponent(art.artifact_id)}/insert`,
              { method: "POST" },
            );
            if (toastIfMiss(result, toast, "Artifact insert unavailable")) return;
            toast("Artifact inserted into run context", "success");
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        });
        li.appendChild(insertBtn);
      }
      list.appendChild(li);
    }
  } catch (e) {
    list.replaceChildren();
    const missBody = { via: "broker_miss", error: String(e.message || e), feature: "context_artifacts" };
    const li = document.createElement("li");
    li.className = "context-artifact-miss";
    li.dataset.testid = "maker-context-artifact-miss";
    li.textContent =
      formatDomainMissMessage(missBody, "Context artifacts unavailable") || "Context artifacts unavailable";
    list.appendChild(li);
    toastIfMiss(missBody, toast, "Context artifacts unavailable");
  }
}

export async function renderMemoryInfluence(runId) {
  try {
    const mem = await apiJson(`/runs/${runId}/memory-influence`);
    const tbody = document.querySelector("#memory-influence-table tbody");
    if (!tbody) return;
    tbody.replaceChildren();
    if (isDomainPeelMiss(mem)) {
      const tr = document.createElement("tr");
      tr.dataset.testid = "maker-memory-influence-miss";
      const td = document.createElement("td");
      td.colSpan = 3;
      td.textContent =
        formatDomainMissMessage(mem, "Memory influence unavailable") || "Memory influence unavailable";
      tr.appendChild(td);
      tbody.appendChild(tr);
      toastIfMiss(mem, toast, "Memory influence unavailable");
      return;
    }
    for (const row of mem.rows || []) {
      const tr = document.createElement("tr");
      tr.dataset.testid = "maker-memory-influence-row";
      tr.innerHTML = `<td>${row.stage || ""}</td><td>${row.hits || ""}</td><td>${row.query_digest || ""}</td>`;
      tbody.appendChild(tr);
    }
  } catch (e) {
    toast(String(e.message || e), "error");
  }
}
