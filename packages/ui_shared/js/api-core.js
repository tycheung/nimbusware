export function parseApiErrorBody(text) {
  try {
    const prob = JSON.parse(text);
    return prob.detail || prob.title || text;
  } catch {
    return text;
  }
}

/**
 * @param {string} apiBase - e.g. "/v1"
 * @param {Record<string, string>} extraHeaders
 * @param {string} path
 * @param {RequestInit} [options]
 */
export async function fetchJson(apiBase, extraHeaders, path, options = {}) {
  const base = apiBase.replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...extraHeaders,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    const detail = parseApiErrorBody(text);
    const err = new Error(`${res.status}: ${String(detail).slice(0, 400)}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}
