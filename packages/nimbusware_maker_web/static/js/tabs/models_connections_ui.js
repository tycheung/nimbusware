import { apiJson, toast } from "../api-client.js";
import { maskSecret } from "./models_hub_nav.js";

export async function wireApiConnectionsPanel(root) {
  let providerPresets = [];
  let savedConnections = [];

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
      card.innerHTML = `
        <h4>${preset.label}</h4>
        <p class="muted">Kind: API key</p>
        <form class="model-hub-api-form">
          <label>API key <input type="password" name="api_key" placeholder="${maskSecret(existing?.secret_set)}" autocomplete="off" /></label>
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

  await loadApiConnections();
}
