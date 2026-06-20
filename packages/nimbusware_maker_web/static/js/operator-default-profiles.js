export const AUTOPILOT_PROFILE_STORAGE_KEY = "maker_default_autopilot_profile_id";
export const ENFORCEMENT_PROFILE_STORAGE_KEY = "maker_default_enforcement_profile_id";

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

export function applyDefaultProfilesToPayload(payload) {
  const { autopilot, enforcement } = defaultOperatorProfileIds();
  if (autopilot) payload.autopilot_profile_id = autopilot;
  if (enforcement) payload.enforcement_profile_id = enforcement;
  return payload;
}
