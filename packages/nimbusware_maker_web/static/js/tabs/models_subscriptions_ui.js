import { apiJson, toast } from "../api-client.js";

export async function wireSubscriptionConnectionsPanel(root) {
  let subscriptionPresets = [];
  let savedConnections = [];
  let oauthStatusByProvider = new Map();

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

  function startOAuthConnect(preset) {
    const status = oauthStatusByProvider.get(preset.id);
    const path = status?.authorize_path;
    if (!path) {
      toast("OAuth is not configured for this install", "error");
      return;
    }
    window.location.assign(path);
  }

  function renderCards() {
    const host = root.querySelector("#models-subscription-cards");
    if (!host) return;
    host.replaceChildren();
    for (const preset of subscriptionPresets) {
      const existing = connectionForPreset(preset.id);
      const connected = existing?.secret_set && existing?.last_probe_ok !== false;
      const oauthReady = Boolean(oauthStatusByProvider.get(preset.id)?.oauth_ready);
      const card = document.createElement("article");
      card.className = "model-hub-card";
      card.dataset.testid = `maker-subscription-card-${preset.id}`;
      card.innerHTML = `
        <h4>${preset.label}</h4>
        <p class="muted">${preset.oauth_hint || "Desktop subscription — keys stay on this machine."}</p>
        <p class="muted probe-status">${connected ? "Connected on this device" : "Not connected"}</p>
        <div class="actions">
          ${
            oauthReady
              ? '<button type="button" class="primary oauth-btn">Connect with OAuth</button>'
              : ""
          }
          <button type="button" class="${oauthReady ? "secondary" : "primary"} connect-btn" data-connected="1">${
            oauthReady ? "Connect on this device" : "Connect"
          }</button>
          <button type="button" class="secondary disconnect-btn">Disconnect</button>
        </div>`;
      card.querySelector(".oauth-btn")?.addEventListener("click", () => startOAuthConnect(preset));
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
      const [presetsBody, connBody, oauthBody] = await Promise.all([
        apiJson("/platform/provider-presets"),
        apiJson("/platform/provider-connections"),
        apiJson("/platform/provider-subscriptions/oauth/status").catch(() => ({ providers: [] })),
      ]);
      subscriptionPresets = presetsBody.subscription_providers || [];
      savedConnections = connBody.connections || [];
      oauthStatusByProvider = new Map(
        (oauthBody.providers || []).map((row) => [row.provider_id, row]),
      );
      renderCards();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }

  await loadSubscriptions();
}
