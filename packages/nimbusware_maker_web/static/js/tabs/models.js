import { apiJson, toast } from "../api-client.js";

export async function mountModels(root) {
  root.innerHTML = `<table id="models-table"><thead><tr><th>Model</th><th>Fit</th><th></th></tr></thead><tbody></tbody></table>
    <button type="button" id="models-apply-preset">Apply recommended preset</button>`;

  const hw = await apiJson("/platform/hardware");
  const tbody = root.querySelector("#models-table tbody");
  for (const row of hw.models_ranked || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.model || row.name || "?"}</td><td>${row.fit_level || ""}</td><td></td>`;
    tbody?.appendChild(tr);
  }

  root.querySelector("#models-apply-preset")?.addEventListener("click", async () => {
    await apiJson("/platform/models/apply-preset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: "recommended" }),
    });
    toast("Preset applied", "success");
  });
}
