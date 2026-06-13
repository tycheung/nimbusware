export function theaterLineText(data) {
  if (!data || typeof data !== "object") return "";
  if (typeof data.message === "string" && data.message.trim()) return data.message.trim();
  if (typeof data.headline === "string" && data.headline.trim()) {
    const body = typeof data.body_md === "string" ? data.body_md.trim() : "";
    return body ? `${data.headline.trim()} — ${body.slice(0, 200)}` : data.headline.trim();
  }
  if (Array.isArray(data.messages)) {
    return data.messages.map((m) => theaterLineText(m)).filter(Boolean).join(" · ");
  }
  return "";
}

export function openSseStream(path, { onMessage, onEvent, onError, maxRetries = 8 } = {}) {
  const base = (window.__NIMBUSWARE__?.api_base || "/v1").replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  let retries = 0;
  let source = null;
  let closed = false;

  function connect() {
    source = new EventSource(url);
    source.onmessage = (ev) => {
      retries = 0;
      if (onMessage) onMessage(ev);
    };
    if (onEvent && typeof onEvent === "object") {
      for (const [name, handler] of Object.entries(onEvent)) {
        if (typeof handler !== "function") continue;
        source.addEventListener(name, (ev) => {
          retries = 0;
          handler(ev);
        });
      }
    }
    source.onerror = () => {
      source.close();
      if (closed) return;
      retries += 1;
      if (onError) onError(retries);
      if (retries > maxRetries) return;
      const delay = Math.min(30000, 500 * 2 ** retries);
      setTimeout(connect, delay);
    };
  }

  connect();

  return {
    close() {
      closed = true;
      if (source) source.close();
    },
  };
}

export function parseSseJson(ev) {
  try {
    return JSON.parse(ev.data);
  } catch {
    return null;
  }
}
