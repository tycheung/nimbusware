import { fetchJson } from "../../../ui_shared/js/api-core.js";

export function getBootstrap() {
  return window.__NIMBUSWARE__ || { api_base: "/v1" };
}

export function apiBase() {
  const b = getBootstrap();
  return (b.api_base || "/v1").replace(/\/$/, "");
}

export function adminHeaders() {
  const token = sessionStorage.getItem("nimbusware_admin_token");
  return token ? { "X-Nimbusware-Admin-Token": token } : {};
}

export async function apiJson(path, options = {}) {
  return fetchJson(apiBase(), adminHeaders(), path, options);
}

export function toast(message, kind = "info") {
  window.dispatchEvent(
    new CustomEvent("maker-toast", { detail: { message, kind } }),
  );
}
