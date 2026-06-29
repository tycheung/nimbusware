import { apiJson, toast } from "../api-client.js";
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
    const catalog = await apiJson("/platform/industry-critic-packs");
    for (const pack of catalog.packs || []) {
      const el = document.createElement("option");
      el.value = pack.id;
      el.textContent = pack.label || pack.id;
      if (pack.domain) el.title = pack.domain;
      select.appendChild(el);
    }
  } catch {
    /* optional */
  }
  try {
    const body = await apiJson("/platform/safe-coding-preferences");
    const packs = body.industry_critic_pack_ids || [];
    select.value = packs[0] || "";
  } catch {
    /* optional */
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
