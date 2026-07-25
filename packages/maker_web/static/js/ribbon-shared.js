import { toast } from "./api-client.js";
import { isDomainPeelMiss, toastIfMiss } from "./broker_miss.js"; // sak500-b

export function ribbonControl(root, dataAttr, id) {
  return root.querySelector(`[${dataAttr}]`) || (id ? root.querySelector(`#${id}`) : null);
}

export function populateProfileSelect(select, profiles) {
  if (!select) return;
  select.replaceChildren();
  const custom = document.createElement("option");
  custom.value = "";
  custom.textContent = "— custom —";
  select.appendChild(custom);
  for (const p of profiles) {
    const opt = document.createElement("option");
    opt.value = p.profile_id;
    opt.textContent = p.name || p.profile_id;
    select.appendChild(opt);
  }
}

export async function loadPlatformUserProfiles(apiJsonFn, path) {
  try {
    const body = await apiJsonFn(path);
    if (isDomainPeelMiss(body)) {
      toastIfMiss(body, toast, "User profiles unavailable");
      return [];
    }
    return body.profiles || [];
  } catch (e) {
    toast(String(e.message || e), "error");
    return [];
  }
}
