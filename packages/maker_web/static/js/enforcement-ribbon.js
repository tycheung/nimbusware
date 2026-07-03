import { apiJson, toast } from "./api-client.js";
import { loadPlatformUserProfiles, populateProfileSelect, ribbonControl } from "./ribbon-shared.js";

export async function loadEnforcementUserProfiles() {
  return loadPlatformUserProfiles(apiJson, "/platform/enforcement/user-profiles");
}

export function applyEnforcementProfileToControls(root, profile) {
  const slider = ribbonControl(root, "data-enforcement-slider", "enforcement-slider");
  const label = ribbonControl(root, "data-enforcement-level-label", "enforcement-level-label");
  const summary = ribbonControl(root, "data-enforcement-summary", "enforcement-summary");
  if (slider) slider.value = String(profile.level ?? 5);
  if (label) label.textContent = String(profile.level ?? 5);
  if (summary) {
    summary.textContent = profile.name || `Level ${profile.level ?? 5}`;
  }
}

export async function wireEnforcementRibbon(root, runId) {
  const slider = ribbonControl(root, "data-enforcement-slider", "enforcement-slider");
  const label = ribbonControl(root, "data-enforcement-level-label", "enforcement-level-label");
  const summary = ribbonControl(root, "data-enforcement-summary", "enforcement-summary");
  const profileSelect = ribbonControl(
    root,
    "data-enforcement-profile-select",
    "enforcement-profile-select",
  );
  if (!slider || !runId) return;

  slider.addEventListener("input", async () => {
    if (label) label.textContent = String(slider.value);
    try {
      const preset = await apiJson(
        `/enforcement/presets/${encodeURIComponent(slider.value)}`,
      );
      if (summary) summary.textContent = preset.name || `Level ${slider.value}`;
    } catch {
      if (summary) summary.textContent = `Level ${slider.value}`;
    }
  });

  const profiles = await loadEnforcementUserProfiles();
  populateProfileSelect(profileSelect, profiles);
  profileSelect?.addEventListener("change", async (ev) => {
    const pid = ev.target?.value;
    if (!pid) return;
    const match = profiles.find((p) => p.profile_id === pid);
    if (match) applyEnforcementProfileToControls(root, match);
  });

  ribbonControl(root, "data-enforcement-save", "enforcement-save-btn")?.addEventListener(
    "click",
    async () => {
    const level = Number(slider.value || 5);
    try {
      const body = await apiJson(`/runs/${encodeURIComponent(runId)}/enforcement`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level }),
      });
      toast(`Enforcement level ${level} applied`, "success");
      if (summary) summary.textContent = body.name || `Level ${level}`;
      root.dispatchEvent(new CustomEvent("enforcement-updated", { detail: { level } }));
    } catch (e) {
      toast(String(e.message || e), "error");
    }
    },
  );

  ribbonControl(
    root,
    "data-enforcement-profile-save",
    "enforcement-profile-save-btn",
  )?.addEventListener("click", async () => {
    const level = Number(slider.value || 5);
    const profileId = window.prompt("Profile id (slug)", "default")?.trim();
    if (!profileId) return;
    const name = window.prompt("Display name", profileId)?.trim() || profileId;
    try {
      await apiJson(`/platform/enforcement/user-profiles/${encodeURIComponent(profileId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, level }),
      });
      toast(`Saved enforcement profile ${profileId}`, "success");
      const refreshed = await loadEnforcementUserProfiles();
      profiles.splice(0, profiles.length, ...refreshed);
      populateProfileSelect(profileSelect, profiles);
      if (profileSelect) profileSelect.value = profileId;
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  try {
    const ep = await apiJson(`/runs/${encodeURIComponent(runId)}/enforcement`);
    if (slider) slider.value = String(ep.level ?? 5);
    if (label) label.textContent = String(ep.level ?? 5);
    if (summary) summary.textContent = ep.name || `Level ${ep.level ?? 5}`;
    root.dispatchEvent(
      new CustomEvent("enforcement-loaded", { detail: { level: ep.level, name: ep.name } }),
    );
  } catch {
    if (summary) summary.textContent = "";
  }
}

export function enforcementRibbonHtml({ compact = false, rootId = "" } = {}) {
  const tag = compact ? "div" : "section";
  const idAttr = rootId ? ` id="${rootId}"` : "";
  const panelClass = compact ? "" : " panel";
  return `
    <${tag}${idAttr} class="enforcement-ribbon${panelClass}${compact ? " enforcement-ribbon--compact" : ""}" data-testid="maker-enforcement-ribbon">
      <h4>Enforcement depth</h4>
      <label>Level 0–10
        <input type="range" data-enforcement-slider min="0" max="10" value="5" data-testid="maker-enforcement-slider" />
      </label>
      <span data-enforcement-level-label>5</span>
      <p class="muted" data-enforcement-summary data-testid="maker-enforcement-summary"></p>
      <div class="actions">
        <label>Saved profile
          <select data-enforcement-profile-select data-testid="maker-enforcement-profile-select">
            <option value="">— custom —</option>
          </select>
        </label>
        <button type="button" data-enforcement-profile-save data-testid="maker-enforcement-profile-save">Save profile</button>
        <button type="button" data-enforcement-save data-testid="maker-enforcement-save">Apply to run</button>
      </div>
    </${tag}>`;
}
