export const AUTOPILOT_PROFILE_STORAGE_KEY = "maker_default_autopilot_profile_id";
export const ENFORCEMENT_PROFILE_STORAGE_KEY = "maker_default_enforcement_profile_id";
export const WORKFLOW_PROFILE_STORAGE_KEY = "maker_default_workflow_profile";
export const ARCHETYPE_SUBCHOICE_STORAGE_KEY = "maker_archetype_subchoice";

let _bootstrapDefaults = null;

export function setBootstrapDefaultProfiles(defaults) {
  _bootstrapDefaults = defaults && typeof defaults === "object" ? defaults : null;
}

export function applyBootstrapDefaultProfilesIfUnset() {
  const d = _bootstrapDefaults;
  if (!d) return;
  if (!readStoredProfileId(AUTOPILOT_PROFILE_STORAGE_KEY) && d.autopilot_profile_id) {
    writeStoredProfileId(AUTOPILOT_PROFILE_STORAGE_KEY, d.autopilot_profile_id);
  }
  if (!readStoredProfileId(ENFORCEMENT_PROFILE_STORAGE_KEY) && d.enforcement_profile_id) {
    writeStoredProfileId(ENFORCEMENT_PROFILE_STORAGE_KEY, d.enforcement_profile_id);
  }
  if (!readStoredProfileId(WORKFLOW_PROFILE_STORAGE_KEY) && d.workflow_profile) {
    writeStoredProfileId(WORKFLOW_PROFILE_STORAGE_KEY, d.workflow_profile);
  }
}

export function readStoredProfileId(key) {
  return localStorage.getItem(key)?.trim() || "";
}

export function writeStoredProfileId(key, value) {
  const val = String(value || "").trim();
  if (val) localStorage.setItem(key, val);
  else localStorage.removeItem(key);
}

export function defaultAutopilotProfileId() {
  return readStoredProfileId(AUTOPILOT_PROFILE_STORAGE_KEY);
}

export function defaultEnforcementProfileId() {
  return readStoredProfileId(ENFORCEMENT_PROFILE_STORAGE_KEY);
}

export function defaultOperatorProfileIds() {
  return {
    autopilot: defaultAutopilotProfileId(),
    enforcement: defaultEnforcementProfileId(),
  };
}

export function defaultWorkflowProfileId() {
  return readStoredProfileId(WORKFLOW_PROFILE_STORAGE_KEY);
}

export function applyDefaultProfilesToPayload(payload) {
  const { autopilot, enforcement } = defaultOperatorProfileIds();
  const workflow = defaultWorkflowProfileId();
  if (autopilot) payload.autopilot_profile_id = autopilot;
  if (enforcement) payload.enforcement_profile_id = enforcement;
  if (workflow) payload.workflow_profile = workflow;
  return payload;
}
