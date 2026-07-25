import { apiJson, toast } from "../api-client.js";
import { toastIfMiss } from "../broker_miss.js";
import { isSafeCodingUx } from "../safe-coding-ux.js";

export async function wireSafeCodingSettingsPanel(root) {
  const host = root.querySelector("#settings-safe-coding-panel");
  if (!host || !isSafeCodingUx()) return;
  host.hidden = false;
  const select = host.querySelector("#settings-industry-critic-pack");
  if (!select) return;
  select.replaceChildren();
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "(none)";
  select.appendChild(none);
  try {
    const catalog = await apiJson("/platform/industry-critic-packs").catch((e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "industry_critic_packs",
      packs: [],
    }));
    if (toastIfMiss(catalog, toast, "Industry critic packs unavailable")) {
      /* continue with empty select */
    } else {
      for (const pack of catalog.packs || []) {
        const el = document.createElement("option");
        el.value = pack.id;
        el.textContent = pack.label || pack.id;
        if (pack.domain) el.title = pack.domain;
        select.appendChild(el);
      }
    }
  } catch (e) {
    toast(String(e.message || e), "error");
  }
  try {
    const body = await apiJson("/platform/safe-coding-preferences").catch((e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "safe_coding_preferences",
    }));
    if (toastIfMiss(body, toast, "Safe-coding preferences unavailable")) {
      return;
    }
    const packs = body.industry_critic_pack_ids || [];
    select.value = packs[0] || "";
  } catch (e) {
    toast(String(e.message || e), "error");
  }
  host.querySelector("#settings-industry-critic-save")?.addEventListener("click", async () => {
    const packId = select.value.trim();
    try {
      await apiJson("/platform/safe-coding-preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ industry_critic_pack_ids: packId ? [packId] : [] }),
      });
      toast("Industry critic pack saved", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
}
