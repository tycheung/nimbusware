import { plainCheckpointLabel } from "./plain-language.js";
import { loadPlatformUserProfiles, populateProfileSelect, ribbonControl } from "./ribbon-shared.js";

export const AUTOPILOT_CHECKPOINT_CATALOG = [
  "stop_after_run_plan",
  "stop_after_slice_plan",
  "stop_before_workspace_apply",
  "stop_on_slice_test_fail",
  "stop_on_dev_env_regression_fail",
  "stop_on_ui_regression_fail",
  "stop_on_gate_fail",
  "stop_before_factory_complete",
  "stop_at_terminal_review",
];

export function renderAutopilotCheckpoints(mount, selected) {
  if (!mount) return;
  mount.replaceChildren();
  const selectedSet = new Set(selected || []);
  AUTOPILOT_CHECKPOINT_CATALOG.forEach((id) => {
    const label = document.createElement("label");
    label.className = "autopilot-checkpoint";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = id;
    box.dataset.testid = `maker-autopilot-cp-${id}`;
    box.checked = selectedSet.has(id);
    label.appendChild(box);
    label.append(` ${plainCheckpointLabel(id)}`);
    mount.appendChild(label);
  });
}

export function selectedAutopilotCheckpoints(mount) {
  if (!mount) return [];
  return [...mount.querySelectorAll('input[type="checkbox"]:checked')]
    .map((el) => el.value)
    .filter(Boolean);
}

export async function loadAutopilotUserProfiles() {
  return loadPlatformUserProfiles(apiJson, "/platform/autopilot/user-profiles");
}

export function applyAutopilotProfileToControls(root, profile) {
  const slider = ribbonControl(root, "data-autopilot-slider", "autopilot-slider");
  const label = ribbonControl(root, "data-autopilot-level-label", "autopilot-level-label");
  const checkpoints = ribbonControl(root, "data-autopilot-checkpoints", "autopilot-checkpoints");
  if (slider) slider.value = String(profile.level ?? 5);
  if (label) label.textContent = String(profile.level ?? 5);
  renderAutopilotCheckpoints(checkpoints, profile.checkpoints || []);
}

export async function wireAutopilotRibbon(root, runId) {
  const slider = ribbonControl(root, "data-autopilot-slider", "autopilot-slider");
  const label = ribbonControl(root, "data-autopilot-level-label", "autopilot-level-label");
  const checkpointsMount = ribbonControl(
    root,
    "data-autopilot-checkpoints",
    "autopilot-checkpoints",
  );
  const profileSelect = ribbonControl(
    root,
    "data-autopilot-profile-select",
    "autopilot-profile-select",
  );
  if (!slider || !runId) return;

  const syncCheckpointVisibility = () => {
    if (checkpointsMount) checkpointsMount.hidden = Number(slider.value) >= 9;
  };

  slider.addEventListener("input", () => {
    if (label) label.textContent = String(slider.value);
    syncCheckpointVisibility();
  });

  const profiles = await loadAutopilotUserProfiles();
  populateProfileSelect(profileSelect, profiles);
  profileSelect?.addEventListener("change", async (ev) => {
    const pid = ev.target?.value;
    if (!pid) return;
    const match = profiles.find((p) => p.profile_id === pid);
    if (match) applyAutopilotProfileToControls(root, match);
    syncCheckpointVisibility();
  });

  ribbonControl(root, "data-autopilot-save", "autopilot-save-btn")?.addEventListener(
    "click",
    async () => {
    const level = Number(slider.value || 5);
    const checkpoints = selectedAutopilotCheckpoints(checkpointsMount);
    try {
      await apiJson(`/runs/${encodeURIComponent(runId)}/autopilot`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, checkpoints }),
      });
      toast(`Trust level ${level} applied`, "success");
      root.dispatchEvent(new CustomEvent("autopilot-updated", { detail: { level } }));
    } catch (e) {
      toast(String(e.message || e), "error");
    }
    },
  );

  ribbonControl(root, "data-autopilot-profile-save", "autopilot-profile-save-btn")?.addEventListener(
    "click",
    async () => {
    const level = Number(slider.value || 5);
    const checkpoints = selectedAutopilotCheckpoints(checkpointsMount);
    const profileId = window.prompt("Profile id (slug)", "default")?.trim();
    if (!profileId) return;
    const name = window.prompt("Display name", profileId)?.trim() || profileId;
    try {
      await apiJson(`/platform/autopilot/user-profiles/${encodeURIComponent(profileId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, level, checkpoints }),
      });
      toast(`Saved profile ${profileId}`, "success");
      const refreshed = await loadAutopilotUserProfiles();
      profiles.splice(0, profiles.length, ...refreshed);
      populateProfileSelect(profileSelect, profiles);
      if (profileSelect) profileSelect.value = profileId;
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  try {
    const ap = await apiJson(`/runs/${encodeURIComponent(runId)}/autopilot`);
    if (slider) slider.value = String(ap.level ?? 5);
    if (label) label.textContent = String(ap.level ?? 5);
    renderAutopilotCheckpoints(checkpointsMount, ap.checkpoints || []);
    syncCheckpointVisibility();
    root.dispatchEvent(
      new CustomEvent("autopilot-loaded", { detail: { level: ap.level, name: ap.name } }),
    );
  } catch {
    renderAutopilotCheckpoints(checkpointsMount, []);
    syncCheckpointVisibility();
  }
}

export function autopilotRibbonHtml({ compact = false, rootId = "" } = {}) {
  const tag = compact ? "div" : "section";
  const idAttr = rootId ? ` id="${rootId}"` : "";
  const panelClass = compact ? "" : " panel";
  return `
    <${tag}${idAttr} class="autopilot-ribbon${panelClass}${compact ? " autopilot-ribbon--compact" : ""}" data-testid="maker-autopilot-ribbon">
      <h4>Trust / Autopilot</h4>
      <label>Level 0–10
        <input type="range" data-autopilot-slider min="0" max="10" value="5" data-testid="maker-autopilot-slider" />
      </label>
      <span data-autopilot-level-label>5</span>
      <div data-autopilot-checkpoints class="autopilot-checkpoints" data-testid="maker-autopilot-checkpoints"></div>
      <div class="actions">
        <label>Saved profile
          <select data-autopilot-profile-select data-testid="maker-autopilot-profile-select">
            <option value="">— custom —</option>
          </select>
        </label>
        <button type="button" data-autopilot-profile-save data-testid="maker-autopilot-profile-save">Save profile</button>
        <button type="button" data-autopilot-save data-testid="maker-autopilot-save">Apply to run</button>
      </div>
    </${tag}>`;
}
