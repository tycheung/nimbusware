import { apiJson, toast } from "../api-client.js";

const OPTIMIZER_KEYS = ["headroom", "model_fit", "latency", "cost"];

export async function wireOptimizerWeightsPanel(root) {
  const optimizerFields = root.querySelector("#settings-optimizer-fields");
  if (!optimizerFields) return;
  optimizerFields.replaceChildren();
  for (const key of OPTIMIZER_KEYS) {
    const label = document.createElement("label");
    label.textContent = `${key} `;
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.max = "1";
    input.step = "0.05";
    input.dataset.optimizerKey = key;
    input.dataset.testid = `maker-settings-optimizer-${key}`;
    label.appendChild(input);
    optimizerFields.appendChild(label);
  }
  try {
    const body = await apiJson("/platform/optimizer-weights");
    const weights = body.weights || {};
    for (const input of optimizerFields.querySelectorAll("input[data-optimizer-key]")) {
      const k = input.dataset.optimizerKey;
      if (k && weights[k] != null) input.value = String(weights[k]);
    }
  } catch {
    /* defaults in UI */
  }
  root.querySelector("#settings-optimizer-save")?.addEventListener("click", async () => {
    const weights = {};
    for (const input of optimizerFields.querySelectorAll("input[data-optimizer-key]") || []) {
      weights[input.dataset.optimizerKey] = Number(input.value) || 0;
    }
    try {
      await apiJson("/platform/optimizer-weights", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weights }),
      });
      toast("Optimizer weights saved", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}
