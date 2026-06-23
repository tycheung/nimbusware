import { apiJson, toast } from "../api-client.js";

export async function wireRoutingPresetsPanel(root) {
  async function refreshRoutingPresets() {
    const activeEl = root.querySelector("#settings-routing-active");
    const cloudEl = root.querySelector("#settings-routing-cloud");
    const select = root.querySelector("#settings-routing-select");
    if (!select) return;
    try {
      const body = await apiJson("/platform/routing-presets");
      const presets = body.presets || [];
      const active = String(body.active_preset_id || "local_only");
      select.replaceChildren();
      for (const preset of presets) {
        const opt = document.createElement("option");
        opt.value = String(preset.id || "");
        opt.textContent = String(preset.label || preset.id || "");
        if (opt.value === active) opt.selected = true;
        select.appendChild(opt);
      }
      if (activeEl) {
        activeEl.textContent = `Active preset: ${active}`;
      }
      const probe = body.cloud_preflight || {};
      if (cloudEl) {
        const ok = probe.ok === true;
        cloudEl.textContent = ok
          ? "Cloud preflight: ready"
          : `Cloud preflight: ${probe.message || probe.reason || "not configured"}`;
      }
    } catch (e) {
      if (activeEl) activeEl.textContent = "Routing presets unavailable";
      if (cloudEl) cloudEl.textContent = String(e.message || e);
    }
  }
  await refreshRoutingPresets();

  root.querySelector("#settings-routing-apply")?.addEventListener("click", async () => {
    const select = root.querySelector("#settings-routing-select");
    const presetId = select?.value?.trim();
    if (!presetId) return;
    try {
      const applied = await apiJson("/platform/routing-presets/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset_id: presetId }),
      });
      toast(`Applied routing preset: ${applied.preset_id || presetId}`, "success");
      await refreshRoutingPresets();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}

export async function wireAgentModelsPanel(root) {
  let agentBindingsState = { version: 1, roles: {} };
  let agentProviders = [];

  async function refreshAgentModels() {
    const host = root.querySelector("#settings-agent-models-table");
    if (!host) return;
    try {
      const body = await apiJson("/platform/model-bindings/defaults");
      agentBindingsState = body.defaults || { version: 1, roles: {} };
      agentProviders = body.providers || [];
      const rows = body.roles || [];
      const table = document.createElement("table");
      table.className = "data-table";
      table.innerHTML =
        "<thead><tr><th>Agent role</th><th>Provider</th><th>Model</th></tr></thead>";
      const tbody = document.createElement("tbody");
      for (const row of rows) {
        const role = row.agent_role || "";
        const binding = row.binding || agentBindingsState.roles?.[role] || {};
        const tr = document.createElement("tr");
        tr.dataset.testid = `maker-settings-agent-row-${role}`;
        const providerSelect = document.createElement("select");
        providerSelect.dataset.role = role;
        providerSelect.dataset.field = "provider_id";
        const cloudProviders = agentProviders.filter((p) => p.kind !== "local");
        for (const opt of [{ id: "ollama", label: "Ollama" }, ...cloudProviders]) {
          const o = document.createElement("option");
          o.value = opt.id;
          o.textContent = opt.label || opt.id;
          if ((binding.provider_id || "ollama") === o.value) o.selected = true;
          providerSelect.appendChild(o);
        }
        const modelInput = document.createElement("input");
        modelInput.dataset.role = role;
        modelInput.dataset.field = "model_id";
        modelInput.value = binding.model_id || "";
        modelInput.placeholder = "model id";
        tr.innerHTML = `<td>${row.display_name || role}</td>`;
        const pCell = document.createElement("td");
        pCell.appendChild(providerSelect);
        const mCell = document.createElement("td");
        mCell.appendChild(modelInput);
        tr.appendChild(pCell);
        tr.appendChild(mCell);
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      host.replaceChildren(table);
    } catch (e) {
      host.textContent = String(e.message || e);
    }
  }

  root.querySelector("#settings-agent-models-save")?.addEventListener("click", async () => {
    const host = root.querySelector("#settings-agent-models-table");
    if (!host) return;
    const roles = { ...(agentBindingsState.roles || {}) };
    host.querySelectorAll("[data-role][data-field]").forEach((el) => {
      const role = el.dataset.role;
      const field = el.dataset.field;
      if (!role || !field) return;
      const block = { ...(roles[role] || {}) };
      if (field === "provider_id") {
        block.provider_id = el.value;
        block.provider_kind = el.value === "ollama" ? "local" : "cloud";
      } else {
        block[field] = el.value;
      }
      roles[role] = block;
    });
    try {
      await apiJson("/platform/model-bindings/defaults", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: 1, roles }),
      });
      toast("Agent model bindings saved", "success");
      await refreshAgentModels();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  await refreshAgentModels();
}
