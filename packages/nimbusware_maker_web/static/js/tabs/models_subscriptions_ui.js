import { apiJson, toast } from "../api-client.js";

export async function wireSubscriptionConnectionsPanel(root) {
  let subscriptionPresets = [];
  let savedConnections = [];

  function connectionForPreset(presetId) {
    return savedConnections.find(
      (c) => c.provider_id === presetId && c.connection_kind === "subscription",
    );
  }

  async function linkSubscription(preset, connected) {
    const res = await apiJson("/platform/provider-connections/subscription-link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider_id: preset.id,
        subscription_connected: connected,
      }),
    });
    toast(
      connected ? `${preset.label} linked on this machine` : `${preset.label} disconnected`,
      "success",
    );
    if (res.oauth_hint) {
      toast(String(res.oauth_hint), "info");
    }
    await loadSubscriptions();
  }

  function renderCards() {
    const host = root.querySelector("#models-subscription-cards");
    if (!host) return;
    host.replaceChildren();
    for (const preset of subscriptionPresets) {
      const existing = connectionForPreset(preset.id);
      const connected = existing?.secret_set && existing?.last_probe_ok !== false;
      const card = document.createElement("article");
      card.className = "model-hub-card";
      card.dataset.testid = `maker-subscription-card-${preset.id}`;
      card.innerHTML = `
        <h4>${preset.label}</h4>
        <p class="muted">${preset.oauth_hint || "Desktop subscription — keys stay on this machine."}</p>
        <p class="muted probe-status">${connected ? "Connected on this device" : "Not connected"}</p>
        <div class="actions">
          <button type="button" class="primary connect-btn" data-connected="1">Connect</button>
          <button type="button" class="secondary disconnect-btn">Disconnect</button>
        </div>`;
      card.querySelector(".connect-btn")?.addEventListener("click", async () => {
        try {
          await linkSubscription(preset, true);
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      card.querySelector(".disconnect-btn")?.addEventListener("click", async () => {
        try {
          await linkSubscription(preset, false);
        } catch (e) {
          toast(String(e.message || e), "error");
        }
      });
      host.appendChild(card);
    }
  }

  async function loadSubscriptions() {
    try {
      const [presetsBody, connBody] = await Promise.all([
        apiJson("/platform/provider-presets"),
        apiJson("/platform/provider-connections"),
      ]);
      subscriptionPresets = presetsBody.subscription_providers || [];
      savedConnections = connBody.connections || [];
      renderCards();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  await loadSubscriptions();
}
