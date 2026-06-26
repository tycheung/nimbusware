import { apiJson, toast } from "../api-client.js";
import { isSafeCodingUx } from "../safe-coding-ux.js";

const PACK_OPTIONS = [
  { id: "", label: "(none)" },
  { id: "fintech-api", label: "Fintech API" },
  { id: "healthcare-api", label: "Healthcare API" },
];

export async function wireSafeCodingSettingsPanel(root) {
  const host = root.querySelector("#settings-safe-coding-panel");
  if (!host || !isSafeCodingUx()) return;
  host.hidden = false;
  const select = host.querySelector("#settings-industry-critic-pack");
  if (!select) return;
  select.replaceChildren();
  for (const opt of PACK_OPTIONS) {
    const el = document.createElement("option");
    el.value = opt.id;
    el.textContent = opt.label;
    select.appendChild(el);
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
