import { apiJson, toast } from "../api-client.js";

const PRESETS = [
  { id: "quality", label: "Quality", hint: "Larger context, slower" },
  { id: "balanced", label: "Balanced", hint: "Default trade-off" },
  { id: "speed", label: "Speed", hint: "Smaller context, faster" },
];

function gpuGroupLabel(group, index) {
  if (!Array.isArray(group) || !group.length) return `Pool ${index}`;
  return `Pool ${index}: ${group.join(", ")}`;
}

export async function mountModels(root) {
  root.innerHTML = `
    <div id="models-hardware-strip" class="models-hardware-strip muted"></div>
    <div id="models-filter-bar" class="models-filter-bar">
      <label class="models-filter-item">
        <input type="checkbox" id="models-gpu-only" />
        GPU-only ranking (no CPU spill)
      </label>
      <label id="models-gpu-pool-wrap" class="models-filter-item" hidden>
        GPU pool
        <select id="models-gpu-pool"></select>
      </label>
    </div>
    <div id="models-wizard" class="wizard-panel">
      <p class="muted">Apply an Ollama preset to model routing in three steps.</p>
      <div id="models-step-1">
        <h3>1. Select model</h3>
        <table id="models-ranked-table" class="data-table">
          <thead><tr><th></th><th>Model</th><th>Fit</th><th></th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="models-step-2" hidden>
        <h3>2. Choose preset</h3>
        <div id="models-preset-cards"></div>
      </div>
      <div id="models-step-3" hidden>
        <h3>3. Confirm</h3>
        <p id="models-confirm-text"></p>
        <button type="button" id="models-apply-btn" class="primary">Apply preset</button>
        <button type="button" id="models-back-btn" class="secondary">Back</button>
      </div>
    </div>
    <form id="models-pull-form">
      <label>Pull model <input name="model" placeholder="llama3.2" required /></label>
      <button type="submit">Pull via Ollama</button>
    </form>
    <p id="models-pull-status"></p>
    <p id="models-catalog-info" class="muted"></p>`;

  let selectedModel = null;
  let selectedPreset = "balanced";
  let wizardStep = 1;
  let gpuOnly = false;
  let gpuGroupIndex = 0;

  function showStep(step) {
    wizardStep = step;
    root.querySelector("#models-step-1").hidden = step !== 1;
    root.querySelector("#models-step-2").hidden = step !== 2;
    root.querySelector("#models-step-3").hidden = step !== 3;
  }

  function renderPresetCards() {
    const host = root.querySelector("#models-preset-cards");
    if (!host) return;
    host.innerHTML = PRESETS.map(
      (p) => `
      <label class="preset-card">
        <input type="radio" name="models-preset" value="${p.id}" ${p.id === selectedPreset ? "checked" : ""} />
        <strong>${p.label}</strong>
        <span class="muted">${p.hint}</span>
      </label>`,
    ).join("");
    host.querySelectorAll('input[name="models-preset"]').forEach((input) => {
      input.addEventListener("change", () => {
        selectedPreset = input.value;
        showStep(3);
        updateConfirm();
      });
    });
  }

  function updateConfirm() {
    const el = root.querySelector("#models-confirm-text");
    if (!el || !selectedModel) return;
    el.textContent = `Apply preset "${selectedPreset}" to model "${selectedModel.model_id}" (${selectedModel.fit_level || "unknown fit"}) for model-routing.`;
  }

  function renderHardwareStrip(profile) {
    const strip = root.querySelector("#models-hardware-strip");
    if (!strip || !profile) return;
    const tier = profile.tier || "unknown";
    const ram = profile.ram_available_gb != null ? `${profile.ram_available_gb} GB free` : "RAM n/a";
    const gpuCount = Array.isArray(profile.gpus) ? profile.gpus.length : 0;
    strip.textContent = `Hardware tier: ${tier} · ${ram} · ${gpuCount} GPU(s) detected`;
  }

  function setupGpuPoolSelect(gpuGroups) {
    const wrap = root.querySelector("#models-gpu-pool-wrap");
    const select = root.querySelector("#models-gpu-pool");
    if (!wrap || !select) return;
    if (!Array.isArray(gpuGroups) || gpuGroups.length <= 1) {
      wrap.hidden = true;
      gpuGroupIndex = 0;
      return;
    }
    wrap.hidden = false;
    select.innerHTML = gpuGroups
      .map((group, index) => `<option value="${index}">${gpuGroupLabel(group, index)}</option>`)
      .join("");
    select.value = String(gpuGroupIndex);
    select.onchange = () => {
      gpuGroupIndex = Number.parseInt(select.value, 10) || 0;
      void loadRanked();
    };
  }

  async function loadRanked() {
    const tbody = root.querySelector("#models-ranked-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    selectedModel = null;
    const params = new URLSearchParams({ limit: "30" });
    if (gpuOnly) params.set("gpu_only", "true");
    if (gpuGroupIndex > 0) params.set("gpu_group_index", String(gpuGroupIndex));
    const rankedBody = await apiJson(`/platform/models/ranked?${params.toString()}`);
    for (const row of rankedBody.models || []) {
      const tr = document.createElement("tr");
      const modelId = row.model_id || row.model || row.name || "?";
      tr.innerHTML = `<td><input type="radio" name="models-select" value="${modelId}" /></td>
        <td>${modelId}</td><td>${row.fit_level || ""}</td>`;
      const radio = tr.querySelector('input[name="models-select"]');
      radio?.addEventListener("change", () => {
        selectedModel = { ...row, model_id: modelId };
        renderPresetCards();
        showStep(2);
      });
      const pullBtn = document.createElement("button");
      pullBtn.type = "button";
      pullBtn.textContent = "Pull";
      pullBtn.onclick = () => startPull(modelId);
      const actions = document.createElement("td");
      actions.appendChild(pullBtn);
      tr.appendChild(actions);
      tbody.appendChild(tr);
    }
    renderPresetCards();
    showStep(1);
  }

  try {
    const info = await apiJson("/platform/models/catalog-info");
    const el = root.querySelector("#models-catalog-info");
    if (el) {
      el.textContent = `Catalog: ${info.model_count} models (v${info.version}), updated ${info.updated_at || "unknown"}`;
    }
  } catch {
    /* optional */
  }

  try {
    const hw = await apiJson("/platform/hardware");
    const profile = hw.profile || {};
    renderHardwareStrip(profile);
    setupGpuPoolSelect(profile.gpu_groups);
  } catch {
    /* optional */
  }

  const gpuOnlyInput = root.querySelector("#models-gpu-only");
  gpuOnlyInput?.addEventListener("change", () => {
    gpuOnly = Boolean(gpuOnlyInput.checked);
    void loadRanked();
  });

  await loadRanked();

  root.querySelector("#models-back-btn")?.addEventListener("click", () => {
    if (wizardStep === 3) showStep(2);
    else showStep(1);
  });

  root.querySelector("#models-apply-btn")?.addEventListener("click", async () => {
    if (!selectedModel?.model_id) {
      toast("Select a model first", "error");
      return;
    }
    try {
      const body = await apiJson("/platform/models/apply-preset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_id: selectedModel.model_id,
          preset: selectedPreset,
          target: "model-routing",
        }),
      });
      const hint = body.materialize_hint || "Preset applied";
      toast(hint, "success");
      if (body.preset_applied) {
        const pa = body.preset_applied;
        toast(`Routing: ${pa.model_id} / ${pa.preset}`, "success");
      }
      showStep(1);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

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
}
