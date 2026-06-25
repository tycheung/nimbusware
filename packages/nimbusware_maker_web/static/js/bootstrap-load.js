import {
  applyBootstrapDefaultProfilesIfUnset,
  setBootstrapDefaultProfiles,
} from "./operator-default-profiles.js";

const res = await fetch("/v1/maker/app/bootstrap.json", { headers: { Accept: "application/json" } });
if (res.ok) {
  window.__NIMBUSWARE__ = await res.json();
} else {
  window.__NIMBUSWARE__ = { api_base: "/v1", edition: "individual", quick_mode: false };
}
setBootstrapDefaultProfiles(window.__NIMBUSWARE__?.default_profiles);
applyBootstrapDefaultProfilesIfUnset();
