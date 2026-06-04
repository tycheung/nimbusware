import { apiJson, toast } from "../api-client.js";

export async function mountModels(root) {
  root.innerHTML = `<table id="models-table"><thead><tr><th>Model</th><th>Fit</th><th></th></tr></thead><tbody></tbody></table>
    <form id="models-pull-form">
      <label>Pull model <input name="model" placeholder="llama3.2" required /></label>
      <button type="submit">Pull via Ollama</button>
    </form>
    <p id="models-pull-status"></p>
    <button type="button" id="models-apply-preset">Apply recommended preset</button>`;

  const hw = await apiJson("/platform/hardware");
  const tbody = root.querySelector("#models-table tbody");
  for (const row of hw.models_ranked || []) {
    const tr = document.createElement("tr");
    const modelName = row.model || row.name || "?";
    tr.innerHTML = `<td>${modelName}</td><td>${row.fit_level || ""}</td><td></td>`;
    const pullBtn = document.createElement("button");
    pullBtn.type = "button";
    pullBtn.textContent = "Pull";
    pullBtn.onclick = () => startPull(modelName);
    tr.lastElementChild?.appendChild(pullBtn);
    tbody?.appendChild(tr);
  }

  async function startPull(model) {
    const status = root.querySelector("#models-pull-status");
    try {
      const accepted = await apiJson("/platform/ollama/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      const jobId = accepted.job_id;
      if (!jobId) {
        toast("Pull accepted", "success");
        return;
      }
      for (let i = 0; i < 120; i += 1) {
        const job = await apiJson(`/platform/ollama/pull/${encodeURIComponent(jobId)}`);
        if (status) status.textContent = `Pull ${model}: ${job.status || "…"}`;
        if (job.status === "completed" || job.status === "failed") {
          if (job.status === "failed") toast(job.error || "Pull failed", "error");
          else toast(`Pulled ${model}`, "success");
          return;
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  root.querySelector("#models-pull-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const model = new FormData(ev.target).get("model");
    await startPull(String(model || "").trim());
  });

  root.querySelector("#models-apply-preset")?.addEventListener("click", async () => {
    await apiJson("/platform/models/apply-preset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: "recommended" }),
    });
    toast("Preset applied", "success");
  });
}
