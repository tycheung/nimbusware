export function openSseStream(path, { onMessage, onError, maxRetries = 8 } = {}) {
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
