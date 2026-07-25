import { apiJson, toast } from "../api-client.js";
import { formatDomainMissMessage, isDomainPeelMiss, toastIfMiss } from "../broker_miss.js"; // sak499-b
import { formatBytes } from "./models_hub_nav.js";

export async function startOllamaPull(root, model) {
  const status = root.querySelector("#models-pull-status");
  try {
    const accepted = await apiJson("/platform/ollama/pull", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    if (toastIfMiss(accepted, toast, "Ollama pull unavailable")) return false;
    const jobId = accepted.job_id;
    if (!jobId) {
      toast("Pull accepted", "success");
      return true;
    }
    for (let i = 0; i < 120; i += 1) {
      const job = await apiJson(`/platform/ollama/pull/${encodeURIComponent(jobId)}`);
      if (toastIfMiss(job, toast, "Ollama pull status unavailable")) return false;
      if (status) status.textContent = `Pull ${model}: ${job.status || "…"}`;
      if (job.status === "completed" || job.status === "failed") {
        if (job.status === "failed") toast(job.error || "Pull failed", "error");
        else toast(`Pulled ${model}`, "success");
        return job.status === "completed";
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  } catch (e) {
    toast(String(e.message || e), "error");
  }
  return false;
}

export async function refreshOllamaPanel(root, { onPullComplete } = {}) {
  const statusEl = root.querySelector("#models-ollama-status");
  const actionsEl = root.querySelector("#models-ollama-actions");
  const listEl = root.querySelector("#models-installed-list");
  if (!statusEl || !actionsEl || !listEl) return;
  const pullAndRefresh = async (name) => {
    const ok = await startOllamaPull(root, name);
    if (ok) await onPullComplete?.();
    else await refreshOllamaPanel(root, { onPullComplete });
  };
  try {
    const body = await apiJson("/platform/ollama/models").catch((e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "ollama_models",
      reachable: false,
      models: [],
    }));
    if (isDomainPeelMiss(body)) {
      statusEl.textContent =
        formatDomainMissMessage(body, "Ollama models unavailable") || "Ollama models unavailable";
      toastIfMiss(body, toast, "Ollama models unavailable");
      actionsEl.replaceChildren();
      listEl.replaceChildren();
      return;
    }
    const dot = body.reachable ? "●" : "○";
    statusEl.textContent = `Ollama: ${dot} ${body.reachable ? "Running" : "Not reachable"} at ${body.base_url}`;
    actionsEl.replaceChildren();
    if (!body.reachable) {
      const installBtn = document.createElement("button");
      installBtn.type = "button";
      installBtn.className = "primary";
      installBtn.dataset.testid = "maker-ollama-install";
      installBtn.textContent = "Install Ollama";
      installBtn.onclick = async () => {
        try {
          const res = await apiJson("/platform/ollama/bootstrap", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          if (toastIfMiss(res, toast, "Ollama bootstrap unavailable")) return;
          toast(res.message || (res.ok ? "Ollama ready" : "Install failed"), res.ok ? "success" : "error");
          await refreshOllamaPanel(root, { onPullComplete });
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      };
      actionsEl.appendChild(installBtn);
    }
    listEl.replaceChildren();
    if (Array.isArray(body.models) && body.models.length) {
      const table = document.createElement("table");
      table.className = "data-table";
      table.innerHTML = "<thead><tr><th>Model</th><th>Size</th><th></th></tr></thead>";
      const tbody = document.createElement("tbody");
      for (const m of body.models) {
        const tr = document.createElement("tr");
        const name = m.name || "?";
        tr.innerHTML = `<td>${name}</td><td>${formatBytes(m.size_bytes)}</td><td></td>`;
        const cell = tr.querySelector("td:last-child");
        const pullBtn = document.createElement("button");
        pullBtn.type = "button";
        pullBtn.textContent = "Pull update";
        pullBtn.onclick = () => pullAndRefresh(name);
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "secondary";
        delBtn.textContent = "Delete";
        delBtn.onclick = async () => {
          try {
            const res = await apiJson(`/platform/ollama/models/${encodeURIComponent(name)}`, {
              method: "DELETE",
            });
            if (toastIfMiss(res, toast, "Ollama delete unavailable")) return;
            toast(`Deleted ${name}`, "success");
            await refreshOllamaPanel(root, { onPullComplete });
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        };
        cell?.appendChild(pullBtn);
        cell?.appendChild(delBtn);
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      listEl.appendChild(table);
    } else if (body.reachable) {
      listEl.textContent = "No models installed yet — pull one below.";
    }
  } catch (e) {
    statusEl.textContent = `Ollama status unavailable: ${e.message || e}`;
  }
}
