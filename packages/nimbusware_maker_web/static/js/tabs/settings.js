import { apiJson, toast } from "../api-client.js";

const GOVERNOR_KEYS = new Set([
  "NIMBUSWARE_MAX_SYSTEM_RAM_PCT",
  "NIMBUSWARE_MAX_VRAM_PCT",
  "NIMBUSWARE_HW_AUTO_ADJUST",
]);

function labelForKey(catalog, key) {
  const groups = catalog?.groups;
  if (!groups || typeof groups !== "object") return key;
  for (const defs of Object.values(groups)) {
    if (!Array.isArray(defs)) continue;
    for (const item of defs) {
      if (item?.key === key && item?.label) return `${item.label} (${key})`;
    }
  }
  return key;
}

function storedValue(stored, key, fallback) {
  if (stored && stored[key] != null && stored[key] !== "") return String(stored[key]);
  return fallback;
}

function truthySetting(raw) {
  const v = String(raw ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}

function renderGovernorPreview(gov) {
  const el = document.querySelector("#governor-preview");
  if (!el || !gov) return;
  const parallel = gov.max_parallel_writer_stages ?? "—";
  const tier = gov.hardware_tier ?? "—";
  el.textContent = `Effective preview: tier ${tier}, max parallel writer stages ${parallel}`;
}

export async function mountSettings(root) {
  const [me, catalog] = await Promise.all([
    apiJson("/settings/me"),
    apiJson("/settings/catalog").catch(() => null),
  ]);
  const stored = me.stored || me.values || me.settings || me;

  root.innerHTML = `
    <section id="governor-panel" class="panel">
      <h3>Resource governor</h3>
      <p id="governor-hardware-summary" class="muted"></p>
      <form id="governor-form">
        <label>
          Max system RAM %
          <input type="range" id="gov-ram-pct" name="NIMBUSWARE_MAX_SYSTEM_RAM_PCT" min="50" max="95" step="1" />
          <span id="gov-ram-pct-val"></span>
        </label>
        <label>
          Max VRAM %
          <input type="range" id="gov-vram-pct" name="NIMBUSWARE_MAX_VRAM_PCT" min="50" max="95" step="1" />
          <span id="gov-vram-pct-val"></span>
        </label>
        <label>
          <input type="checkbox" id="gov-auto-adjust" name="NIMBUSWARE_HW_AUTO_ADJUST" />
          Auto-adjust limits to detected hardware tier
        </label>
        <p id="governor-preview" class="muted"></p>
        <button type="submit" class="primary">Save governor</button>
      </form>
    </section>
    <form id="settings-form"></form>
    <p class="muted" id="reresearch-help">
      <strong>Re-research on plan fail</strong> (<code>NIMBUSWARE_RERESARCH_MISSING_CONTEXT</code>):
      when enabled, the pipeline may re-run research after planner missing-context failures.
    </p>`;

  const ramPct = storedValue(stored, "NIMBUSWARE_MAX_SYSTEM_RAM_PCT", "75");
  const vramPct = storedValue(stored, "NIMBUSWARE_MAX_VRAM_PCT", "85");
  const autoAdjust = truthySetting(storedValue(stored, "NIMBUSWARE_HW_AUTO_ADJUST", "1"));

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
  await refreshHardwarePreview();

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

  const form = root.querySelector("#settings-form");
  const entries = Object.entries(stored).filter(
    ([key, val]) =>
      !GOVERNOR_KEYS.has(key) &&
      (typeof val === "string" || typeof val === "number" || typeof val === "boolean"),
  );
  for (const [key, val] of entries) {
    const label = document.createElement("label");
    label.textContent = labelForKey(catalog, key);
    const input = document.createElement("input");
    input.name = key;
    input.value = String(val);
    label.appendChild(input);
    form?.appendChild(label);
  }
  const btn = document.createElement("button");
  btn.type = "submit";
  btn.textContent = "Save other settings";
  btn.className = "primary";
  form?.appendChild(btn);

  form?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(form);
    const patch = Object.fromEntries(fd.entries());
    await apiJson("/settings/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: patch }),
    });
    toast("Settings saved", "success");
  });
}
