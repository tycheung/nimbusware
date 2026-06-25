import {
  ARCHETYPE_PRESETS,
  plainCheckpointLabel,
} from "./plain-language.js";
import {
  ARCHETYPE_SUBCHOICE_STORAGE_KEY,
  AUTOPILOT_PROFILE_STORAGE_KEY,
  ENFORCEMENT_PROFILE_STORAGE_KEY,
  WORKFLOW_PROFILE_STORAGE_KEY,
  writeStoredProfileId,
} from "./operator-default-profiles.js";

export function archetypeSubchoice() {
  return localStorage.getItem(ARCHETYPE_SUBCHOICE_STORAGE_KEY)?.trim() || "";
}

export function applyArchetypePreset(presetId) {
  const preset = ARCHETYPE_PRESETS[presetId];
  if (!preset) return null;
  writeStoredProfileId(WORKFLOW_PROFILE_STORAGE_KEY, preset.workflow_profile);
  writeStoredProfileId(AUTOPILOT_PROFILE_STORAGE_KEY, preset.autopilot_profile_id);
  writeStoredProfileId(ENFORCEMENT_PROFILE_STORAGE_KEY, preset.enforcement_profile_id);
  localStorage.setItem(ARCHETYPE_SUBCHOICE_STORAGE_KEY, presetId);
  return preset;
}

export function maybeShowArchetypePicker() {
  const bundle = window.__NIMBUSWARE__?.setup_bundle || "default";
  if (bundle !== "default") return;
  if (archetypeSubchoice()) return;

  const overlay = document.createElement("div");
  overlay.className = "archetype-picker-overlay";
  overlay.dataset.testid = "maker-archetype-picker";
  overlay.innerHTML = `
    <div class="archetype-picker panel" role="dialog" aria-labelledby="archetype-picker-title">
      <h2 id="archetype-picker-title">How will you use Nimbusware?</h2>
      <p class="muted">Pick a starting preset. You can change this later in Settings.</p>
      <div class="archetype-picker-actions">
        <button type="button" class="primary" data-archetype="safe_coding" data-testid="maker-archetype-safe">
          Safe Coding
          <span class="muted block">Extra checkpoints, plain guidance, approval before apply</span>
        </button>
        <button type="button" data-archetype="engineer" data-testid="maker-archetype-engineer">
          Engineer workspace
          <span class="muted block">Collab-ready micro-slices with gates</span>
        </button>
      </div>
    </div>`;

  overlay.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-archetype]");
    if (!btn) return;
    applyArchetypePreset(btn.getAttribute("data-archetype"));
    overlay.remove();
  });

  document.body.appendChild(overlay);
}

export { plainCheckpointLabel };
