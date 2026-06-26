import { apiJson, toast } from "../api-client.js";
import {
  AUTOPILOT_PROFILE_STORAGE_KEY,
  ENFORCEMENT_PROFILE_STORAGE_KEY,
  writeStoredProfileId,
} from "../operator-default-profiles.js";
import { loadPlatformUserProfiles, populateProfileSelect } from "../ribbon-shared.js";
import { renderCriticReliabilityPanel, loadRunOrFleetCriticReliability } from "../critic-reliability-panel.js";
import { renderLaunchScorecard } from "../launch-scorecard.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { wireAgentModelsPanel, wireRoutingPresetsPanel } from "./settings_agent_routing_ui.js";
import { wireMemoryLibraryPanel, wireStitchCatalogPanel } from "./settings_memory_stitch_ui.js";
import { wireOptimizerWeightsPanel } from "./settings_optimizer_ui.js";
import { GOVERNOR_KEYS, wireGovernorPanel } from "./settings_governor_ui.js";
import { settingsShellHtml } from "./settings_shell_html.js";

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

export async function mountSettings(root) {
  const [me, catalog] = await Promise.all([
    apiJson("/settings/me"),
    apiJson("/settings/catalog").catch(() => null),
  ]);
  const stored = me.stored || me.values || me.settings || me;

  root.innerHTML = settingsShellHtml();

  await Promise.all([wireRoutingPresetsPanel(root), wireAgentModelsPanel(root)]);

  const collabSection = root.querySelector("#settings-collab");
  const collabToggle = root.querySelector("#settings-collab-enabled");
  if (collabSection && window.__NIMBUSWARE__?.setup_bundle === "default") {
    collabSection.hidden = false;
    try {
      const collab = await apiJson("/platform/collab-settings");
      if (collabToggle) collabToggle.checked = !!collab.collab_enabled;
    } catch {
      /* optional */
    }
    collabToggle?.addEventListener("change", async () => {
      try {
        await apiJson("/platform/collab-settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collab_enabled: !!collabToggle.checked }),
        });
        toast("Collaborative chat setting saved", "success");
      } catch (e) {
        toast(String(e.message || e), "error");
      }
    });
  }

  const chatResume = root.querySelector("#settings-chat-resume");
  if (chatResume) {
    const resumeRaw = localStorage.getItem("maker_chat_resume_session");
    chatResume.checked = resumeRaw == null || resumeRaw === "1" || resumeRaw === "true";
    chatResume.addEventListener("change", () => {
      localStorage.setItem("maker_chat_resume_session", chatResume.checked ? "1" : "0");
      if (!chatResume.checked) sessionStorage.removeItem("maker_chat_session_id");
      toast("Chat session preference saved", "success");
    });
  }

  const trustSelect = root.querySelector("#settings-default-autopilot-profile");
  if (trustSelect) {
    const profiles = await loadPlatformUserProfiles(apiJson, "/platform/autopilot/user-profiles");
    populateProfileSelect(trustSelect, profiles);
    const savedProfile = localStorage.getItem(AUTOPILOT_PROFILE_STORAGE_KEY) || "";
    if (savedProfile) trustSelect.value = savedProfile;
    trustSelect.addEventListener("change", () => {
      writeStoredProfileId(AUTOPILOT_PROFILE_STORAGE_KEY, trustSelect.value);
      toast("Default trust profile saved", "success");
    });
  }

  const enforcementSelect = root.querySelector("#settings-default-enforcement-profile");
  if (enforcementSelect) {
    const profiles = await loadPlatformUserProfiles(apiJson, "/platform/enforcement/user-profiles");
    populateProfileSelect(enforcementSelect, profiles);
    const savedEnforcement = localStorage.getItem(ENFORCEMENT_PROFILE_STORAGE_KEY) || "";
    if (savedEnforcement) enforcementSelect.value = savedEnforcement;
    enforcementSelect.addEventListener("change", () => {
      writeStoredProfileId(ENFORCEMENT_PROFILE_STORAGE_KEY, enforcementSelect.value);
      toast("Default enforcement profile saved", "success");
    });
  }

  await wireGovernorPanel(root, stored);

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

  let presetRunId = resolveRunId();
  if (!presetRunId) presetRunId = await hydrateActiveRun(apiJson);
  const launchHint = root.querySelector("#settings-launch-run-hint");
  if (launchHint) {
    launchHint.textContent = presetRunId
      ? `Using active run ${presetRunId} from session.`
      : "Select a project and start a run to enable launch check without pasting a UUID.";
  }

  root.querySelector("#settings-run-launch-eval")?.addEventListener("click", async () => {
    let id = resolveRunId();
    if (!id) id = await hydrateActiveRun(apiJson);
    if (!id) return toast("No active run — open Progress or start a build", "error");
    const body = root.querySelector("#settings-launch-scorecard");
    try {
      const scorecard = await apiJson(`/runs/${encodeURIComponent(id)}/maker/launch-eval`, {
        method: "POST",
      });
      renderLaunchScorecard(body, scorecard, { testIdPrefix: "maker-settings" });
      toast("Launch check complete", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  await Promise.all([wireMemoryLibraryPanel(root), wireStitchCatalogPanel(root)]);

  if (presetRunId) {
    try {
      const criticBody = await loadRunOrFleetCriticReliability(apiJson, presetRunId);
      renderCriticReliabilityPanel(root.querySelector("#settings-critic-mount"), criticBody, {
        testIdPrefix: "maker-settings-critic",
      });
    } catch {
      renderCriticReliabilityPanel(root.querySelector("#settings-critic-mount"), {}, {
        testIdPrefix: "maker-settings-critic",
      });
    }
  }

  root.querySelector("#settings-critic-probation")?.addEventListener("click", async () => {
    const shelf = root.querySelector("#settings-critic-shelf")?.value?.trim();
    const persona = root.querySelector("#settings-critic-persona")?.value?.trim();
    if (!shelf || !persona) return toast("Enter shelf and persona id", "error");
    const pre = root.querySelector("#settings-critic-probation-body");
    try {
      const body = await apiJson(
        `/personas/${encodeURIComponent(shelf)}/${encodeURIComponent(persona)}/probation-reliability`,
      );
      if (pre) pre.textContent = JSON.stringify(body, null, 2);
    } catch (e) {
      if (pre) pre.textContent = String(e.message || e);
    }
  });

  await wireOptimizerWeightsPanel(root);
}
