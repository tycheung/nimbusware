import { parseApiErrorBody } from "../../../ui_shared/js/api-core.js";
import { mapHttp503PeelMiss } from "../../../ui_shared/js/peel-http.js";
import { isDomainPeelMiss } from "./broker_miss.js";

export function isBootstrapPeelMiss() {
  return isDomainPeelMiss(window.__NIMBUSWARE__); // sak500-h
}

export function getBootstrap() {
  if (window.__NIMBUSWARE__) return window.__NIMBUSWARE__;
  return { api_base: "/v1" };
}

export function apiBase() {
  const b = getBootstrap();
  if (isBootstrapPeelMiss()) {
    return "/v1";
  }
  return (b.api_base || "/v1").replace(/\/$/, "");
}

export function adminHeaders() {
  const token = sessionStorage.getItem("nimbusware_admin_token");
  return token ? { "X-Nimbusware-Admin-Token": token } : {};
}

/** Maker JSON fetch — maps COMPUTE/CAPACITY/MEMORY/LLM=2 HTTP 503 problems to peel miss (`sak493-f` / `sak495-e` / `sak497-g`). */
export async function apiJson(path, options = {}) {
  if (isBootstrapPeelMiss()) {
    return { ...window.__NIMBUSWARE__ };
  }
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...adminHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    const mapped = mapHttp503PeelMiss(res.status, text);
    if (mapped) return mapped;
    const detail = parseApiErrorBody(text);
    const err = new Error(`${res.status}: ${String(detail).slice(0, 400)}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export function toast(message, kind = "info") {
  window.dispatchEvent(
    new CustomEvent("maker-toast", { detail: { message, kind } }),
  );
}
