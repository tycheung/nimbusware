import { apiJson, toast } from "../api-client.js";

const GOVERNOR_KEYS = new Set([
  "NIMBUSWARE_MAX_SYSTEM_RAM_PCT",
  "NIMBUSWARE_MAX_VRAM_PCT",
  "NIMBUSWARE_HW_AUTO_ADJUST",
]);

export { GOVERNOR_KEYS };

function renderGovernorPreview(gov) {
  const el = document.querySelector("#governor-preview");
  if (!el || !gov) return;
  const parallel = gov.max_parallel_writer_stages ?? "—";
  const tier = gov.hardware_tier ?? "—";
  el.textContent = `Effective preview: tier ${tier}, max parallel writer stages ${parallel}`;
}

export function wireGovernorPanel(root, stored) {
  function storedValue(key, fallback) {
    if (stored && stored[key] != null && stored[key] !== "") return String(stored[key]);
    return fallback;
  }

  function truthySetting(raw) {
    const v = String(raw ?? "").trim().toLowerCase();
    return v === "1" || v === "true" || v === "yes";
  }

  const ramPct = storedValue("NIMBUSWARE_MAX_SYSTEM_RAM_PCT", "75");
  const vramPct = storedValue("NIMBUSWARE_MAX_VRAM_PCT", "85");
  const autoAdjust = truthySetting(storedValue("NIMBUSWARE_HW_AUTO_ADJUST", "1"));

  const ramInput = root.querySelector("#gov-ram-pct");
  const vramInput = root.querySelector("#gov-vram-pct");
  const autoInput = root.querySelector("#gov-auto-adjust");
  if (ramInput) ramInput.value = ramPct;
  if (vramInput) vramInput.value = vramPct;
  if (autoInput) autoInput.checked = autoAdjust;

  function syncSliderLabels() {
    const ramVal = root.querySelector("#gov-ram-pct-val");
    const vramVal = root.querySelector("#gov-vram-pct-val");
    if (ramVal && ramInput) ramVal.textContent = `${ramInput.value}%`;
    if (vramVal && vramInput) vramVal.textContent = `${vramInput.value}%`;
  }
  syncSliderLabels();
  ramInput?.addEventListener("input", syncSliderLabels);
  vramInput?.addEventListener("input", syncSliderLabels);

  async function refreshHardwarePreview() {
    try {
      const hw = await apiJson("/platform/hardware");
      const profile = hw.profile || {};
      const summary = root.querySelector("#governor-hardware-summary");
      if (summary) {
        const tier = profile.tier || "unknown";
        const total = profile.ram_total_gb != null ? `${profile.ram_total_gb} GB total` : "RAM n/a";
        const avail = profile.ram_available_gb != null ? `${profile.ram_available_gb} GB free` : "";
        summary.textContent = `Hardware tier: ${tier} · ${total}${avail ? ` · ${avail}` : ""}`;
      }
      renderGovernorPreview(hw.resource_governor);
    } catch {
      /* optional */
    }
  }

  root.querySelector("#governor-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const patch = {
      NIMBUSWARE_MAX_SYSTEM_RAM_PCT: String(ramInput?.value || "75"),
      NIMBUSWARE_MAX_VRAM_PCT: String(vramInput?.value || "85"),
      NIMBUSWARE_HW_AUTO_ADJUST: autoInput?.checked ? "1" : "0",
    };
    await apiJson("/settings/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: patch }),
    });
    toast("Governor settings saved", "success");
    await refreshHardwarePreview();
  });

  return refreshHardwarePreview();
}
