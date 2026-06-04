/**
 * Shared /v1 fetch helper with Problem+JSON errors and optional admin token.
 */
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
  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    headers: {
      Accept: "application/json",
      ...adminHeaders(),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      const prob = JSON.parse(detail);
      detail = prob.detail || prob.title || detail;
    } catch {
      /* plain text */
    }
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
