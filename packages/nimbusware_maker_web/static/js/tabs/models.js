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

function formatBytes(n) {
  if (n == null || Number.isNaN(Number(n))) return "";
  const gb = Number(n) / 1e9;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${(Number(n) / 1e6).toFixed(0)} MB`;
}

function maskSecret(set) {
  return set ? "••••••••••" : "";
}

function hubSectionFromUrl() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const section = params.get("section");
  if (section === "api-connections") return "api-connections";
  return "local";
}

function setHubSection(section) {
  const base = window.location.hash.split("?")[0] || "#/models";
  const params = new URLSearchParams();
  if (section === "api-connections") params.set("section", "api-connections");
  const qs = params.toString();
  window.location.hash = qs ? `${base}?${qs}` : base;
}

function scrollHubSection(root, section) {
  const el = root.querySelector(section === "api-connections" ? "#api-connections" : "#local");
  el?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export async function mountModels(root) {
  root.dataset.testid = "maker-model-hub";
  root.innerHTML = `
    <header class="model-hub-header">
      <h2>Model Hub</h2>
      <nav class="model-hub-nav" aria-label="Model Hub sections">
        <button type="button" class="model-hub-nav-btn" data-section="local">Local models</button>
        <button type="button" class="model-hub-nav-btn" data-section="api-connections">API connections</button>
      </nav>
    </header>
    <section id="local" class="model-hub-section" data-testid="maker-model-hub-local">
      <h3>Local models</h3>
      <div id="models-ollama-status" class="models-ollama-status muted"></div>
      <div id="models-ollama-actions" class="actions"></div>
      <div id="models-installed-list"></div>
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
          <h4>1. Select model</h4>
          <table id="models-ranked-table" class="data-table">
            <thead><tr><th></th><th>Model</th><th>Fit</th><th></th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
        <div id="models-step-2" hidden>
          <h4>2. Choose preset</h4>
          <div id="models-preset-cards"></div>
        </div>
        <div id="models-step-3" hidden>
          <h4>3. Confirm</h4>
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
      <p id="models-catalog-info" class="muted"></p>
    </section>
    <section id="api-connections" class="model-hub-section" data-testid="maker-model-hub-api">
      <h3>API connections</h3>
      <p class="muted">Store API keys on this machine — secrets never appear in chat or audit exports.</p>
      <div id="models-api-cards" class="model-hub-api-cards"></div>
      <article class="model-hub-card model-hub-card--cursor" data-testid="maker-cursor-card">
        <h4>Cursor</h4>
        <p>Cursor Composer is IDE-only — use the MCP bridge for Nimbusware integration.</p>
        <a href="/docs/ide-bridge.md" target="_blank" rel="noopener">Open IDE bridge docs</a>
      </article>
    </section>`;

  let selectedModel = null;
  let selectedPreset = "balanced";
  let wizardStep = 1;
  let gpuOnly = false;
  let gpuGroupIndex = 0;
  let providerPresets = [];
  let savedConnections = [];

  function activateNav(section) {
    root.querySelectorAll(".model-hub-nav-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.section === section);
    });
    scrollHubSection(root, section);
  }

  root.querySelectorAll(".model-hub-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section || "local";
      setHubSection(section);
      activateNav(section);
    });
  });
  activateNav(hubSectionFromUrl());

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
        await refreshOllamaPanel();
        return;
      }
      for (let i = 0; i < 120; i += 1) {
        const job = await apiJson(`/platform/ollama/pull/${encodeURIComponent(jobId)}`);
        if (status) status.textContent = `Pull ${model}: ${job.status || "…"}`;
        if (job.status === "completed" || job.status === "failed") {
          if (job.status === "failed") toast(job.error || "Pull failed", "error");
          else toast(`Pulled ${model}`, "success");
          await refreshOllamaPanel();
          return;
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  async function refreshOllamaPanel() {
    const statusEl = root.querySelector("#models-ollama-status");
    const actionsEl = root.querySelector("#models-ollama-actions");
    const listEl = root.querySelector("#models-installed-list");
    if (!statusEl || !actionsEl || !listEl) return;
    try {
      const body = await apiJson("/platform/ollama/models");
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
            toast(res.message || (res.ok ? "Ollama ready" : "Install failed"), res.ok ? "success" : "error");
            await refreshOllamaPanel();
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
          pullBtn.onclick = () => startPull(name);
          const delBtn = document.createElement("button");
          delBtn.type = "button";
          delBtn.className = "secondary";
          delBtn.textContent = "Delete";
          delBtn.onclick = async () => {
            try {
              await apiJson(`/platform/ollama/models/${encodeURIComponent(name)}`, { method: "DELETE" });
              toast(`Deleted ${name}`, "success");
              await refreshOllamaPanel();
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

  function connectionForPreset(presetId) {
    return savedConnections.find((c) => c.provider_id === presetId);
  }

  async function saveConnection(preset, form) {
    const fd = new FormData(form);
    const payload = {
      connection_id: form.dataset.connectionId || null,
      provider_id: preset.id,
      label: preset.label,
      connection_kind: preset.connection_kind || "api_key",
      base_url: fd.get("base_url") || preset.default_base_url || null,
      default_model_id: fd.get("default_model_id") || null,
      api_key: fd.get("api_key") ? String(fd.get("api_key")) : null,
      subscription_connected: fd.get("subscription_connected") === "on",
    };
    if (payload.connection_kind === "api_key" && !payload.api_key && !form.dataset.connectionId) {
      toast("Enter an API key or update an existing connection", "error");
      return;
    }
    const res = await apiJson("/platform/provider-connections", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    toast("Connection saved", "success");
    if (res.connection?.connection_id) {
      form.dataset.connectionId = res.connection.connection_id;
    }
    await loadApiConnections();
  }

  async function probeConnection(connectionId) {
    const res = await apiJson(`/platform/provider-connections/${encodeURIComponent(connectionId)}/probe`, {
      method: "POST",
    });
    const ok = res.probe?.ok;
    toast(res.probe?.message || (ok ? "Probe OK" : "Probe failed"), ok ? "success" : "error");
    await loadApiConnections();
  }

  function renderApiCards() {
    const host = root.querySelector("#models-api-cards");
    if (!host) return;
    host.replaceChildren();
    for (const preset of providerPresets) {
      if (preset.kind === "local" || preset.id === "custom") continue;
      const existing = connectionForPreset(preset.id);
      const card = document.createElement("article");
      card.className = "model-hub-card";
      card.dataset.testid = `maker-provider-card-${preset.id}`;
      const isSub = preset.connection_kind === "subscription";
      card.innerHTML = `
        <h4>${preset.label}</h4>
        <p class="muted">Kind: ${isSub ? "Subscription" : "API key"}</p>
        <form class="model-hub-api-form">
          ${isSub ? "" : `<label>API key <input type="password" name="api_key" placeholder="${maskSecret(existing?.secret_set)}" autocomplete="off" /></label>`}
          ${isSub ? `<label><input type="checkbox" name="subscription_connected" ${existing?.last_probe_ok ? "checked" : ""} /> Connected via desktop app</label>` : ""}
          <label>Model hint <input name="default_model_id" value="${existing?.default_model_id || ""}" placeholder="gpt-4o" /></label>
          ${preset.id === "custom" || !preset.default_base_url ? `<label>Base URL <input name="base_url" value="${existing?.base_url || ""}" /></label>` : ""}
          <div class="actions">
            <button type="button" class="secondary probe-btn">Test</button>
            <button type="submit" class="primary">Save</button>
          </div>
          <p class="muted probe-status">${existing?.secret_set ? "Key saved" : ""} ${existing?.last_probe_ok === true ? "✓" : existing?.last_probe_ok === false ? "✗" : ""}</p>
        </form>`;
      const form = card.querySelector("form");
      if (existing?.connection_id) form.dataset.connectionId = existing.connection_id;
      form?.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        try {
          await saveConnection(preset, form);
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      card.querySelector(".probe-btn")?.addEventListener("click", async () => {
        if (!form.dataset.connectionId) {
          toast("Save the connection before testing", "error");
          return;
        }
        try {
          await probeConnection(form.dataset.connectionId);
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      host.appendChild(card);
    }
  }

  async function loadApiConnections() {
    try {
      const [presetsBody, connBody] = await Promise.all([
        apiJson("/platform/provider-presets"),
        apiJson("/platform/provider-connections"),
      ]);
      providerPresets = (presetsBody.providers || []).filter(
        (p) => p.connection_kind !== "subscription",
      );
      savedConnections = connBody.connections || [];
      renderApiCards();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
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

  await Promise.all([refreshOllamaPanel(), loadRanked(), loadApiConnections()]);

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

  root.querySelector("#models-pull-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const model = new FormData(ev.target).get("model");
    await startPull(String(model || "").trim());
  });
}
