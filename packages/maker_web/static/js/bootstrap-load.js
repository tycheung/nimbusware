import {
  applyBootstrapDefaultProfilesIfUnset,
  setBootstrapDefaultProfiles,
} from "./operator-default-profiles.js";
import { maybeShowArchetypePicker } from "./archetype-picker.js";
import { mapHttp503PeelMiss } from "../../../ui_shared/js/peel-http.js";
import { toastIfMiss } from "./broker_miss.js";
import { toast } from "./api-client.js";

const res = await fetch("/v1/maker/app/bootstrap.json", {
  headers: { Accept: "application/json" },
});

if (res.ok) {
  window.__NIMBUSWARE__ = await res.json();
} else {
  const text = await res.text();
  const peelMiss = mapHttp503PeelMiss(res.status, text, "app_bootstrap"); // sak497-g
  if (peelMiss) {
    window.__NIMBUSWARE__ = peelMiss;
    toastIfMiss(peelMiss, toast, "App bootstrap unavailable");
  } else {
    window.__NIMBUSWARE__ = { api_base: "/v1", edition: "individual", quick_mode: false };
  }
}
setBootstrapDefaultProfiles(window.__NIMBUSWARE__?.default_profiles);
applyBootstrapDefaultProfilesIfUnset();
maybeShowArchetypePicker();
