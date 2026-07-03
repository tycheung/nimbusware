import { ARCHETYPE_SUBCHOICE_STORAGE_KEY } from "./operator-default-profiles.js";

export function isSafeCodingUx() {
  const archetype = localStorage.getItem(ARCHETYPE_SUBCHOICE_STORAGE_KEY)?.trim() || "";
  if (archetype === "safe_coding") return true;
  const wf = window.__NIMBUSWARE__?.workflow_profile || "";
  return String(wf).trim() === "safe_coding";
}
