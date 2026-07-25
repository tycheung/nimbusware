import { toast } from "./api-client.js";
import { formatDomainMissMessage, isCapacityMiss, isDomainPeelMiss, toastIfMiss } from "./broker_miss.js"; // sak500-g

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

export function openSseStream(
  path,
  {
    onMessage,
    onEvent,
    onError,
    onTerminalFailure,
    maxRetries = 8,
    brokerBacked = false,
    feature = "live_stream",
    terminalFailureMessage = "Live stream unavailable",
  } = {},
) {
  const base = (window.__NIMBUSWARE__?.api_base || "/v1").replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  let retries = 0;
  let source = null;
  let closed = false;

  function connect() {
    source = new EventSource(url);

    function closeAfterPeelMiss(miss) {
      closed = true;
      source?.close();
      handleSsePeelMiss(miss, {
        brokerBacked,
        feature,
        terminalFailureMessage,
        onTerminalFailure,
      });
    }

    source.onmessage = (ev) => {
      const miss = parseSsePeelMiss(ev);
      if (miss) {
        closeAfterPeelMiss(miss);
        return;
      }
      retries = 0;
      if (onMessage) onMessage(ev);
    };
    source.addEventListener("error", (ev) => {
      const miss = parseSsePeelMiss(ev);
      if (!miss) return;
      closeAfterPeelMiss(miss);
    });
    if (onEvent && typeof onEvent === "object") {
      for (const [name, handler] of Object.entries(onEvent)) {
        if (typeof handler !== "function" || name === "error") continue;
        source.addEventListener(name, (ev) => {
          const miss = parseSsePeelMiss(ev);
          if (miss) {
            closeAfterPeelMiss(miss);
            return;
          }
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
      if (retries > maxRetries) {
        if (brokerBacked) {
          toastIfMiss({ via: "broker_miss", feature }, toast, terminalFailureMessage);
        }
        if (onTerminalFailure) onTerminalFailure(retries);
        return;
      }
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

/** Peel miss body from SSE ``event: error`` (or any frame carrying broker_miss) (`sak491-i` / `sak497-j`). */
export function parseSsePeelMiss(ev) {
  const data = parseSseJson(ev);
  if (!data) return null;
  const explicitCapacity =
    data.code === "broker_capacity_only" ||
    data.capacity_source != null ||
    data.fit_via != null;
  if (explicitCapacity && isCapacityMiss(data)) return data;
  if (isDomainPeelMiss(data)) return data;
  if (isCapacityMiss(data)) return data;
  return null;
}

function handleSsePeelMiss(miss, { brokerBacked, feature, terminalFailureMessage, onTerminalFailure }) {
  if (brokerBacked) {
    toastIfMiss(miss, toast, terminalFailureMessage);
  } else if (miss?.error) {
    toast(formatDomainMissMessage(miss, String(miss.error)), "error"); // sak497-j
  }
  if (onTerminalFailure) onTerminalFailure(0);
}
