import { parseSseJson, parseSsePeelMiss } from "./peel_assert";

export type SseStreamHandle = { close: () => void };

export type OpenSseStreamOptions = {
  apiBase: string;
  onMessage?: (ev: MessageEvent) => void;
  onEvent?: Record<string, (ev: MessageEvent) => void>;
  onError?: (retries: number) => void;
  onPeelMiss?: (miss: Record<string, unknown>) => void;
  onTerminalFailure?: (retries: number) => void;
  maxRetries?: number;
  brokerBacked?: boolean;
  feature?: string;
  terminalFailureMessage?: string;
};

/** Admin SSE client with peel miss handling (`sak491-i`; Maker `sse-client.js` parity). */
export function openSseStream(path: string, options: OpenSseStreamOptions): SseStreamHandle {
  const {
    apiBase,
    onMessage,
    onEvent,
    onError,
    onPeelMiss,
    onTerminalFailure,
    maxRetries = 8,
    brokerBacked = false,
    feature = "live_stream",
    terminalFailureMessage = "Live stream unavailable",
  } = options;

  const base = apiBase.replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  let retries = 0;
  let source: EventSource | null = null;
  let closed = false;

  function closeAfterPeelMiss(miss: Record<string, unknown>) {
    closed = true;
    source?.close();
    if (brokerBacked) {
      onPeelMiss?.(miss);
    } else if (miss.error != null) {
      onPeelMiss?.(miss);
    }
    onTerminalFailure?.(0);
  }

  function connect() {
    source = new EventSource(url);

    source.onmessage = (ev) => {
      const miss = parseSsePeelMiss(ev);
      if (miss) {
        closeAfterPeelMiss(miss);
        return;
      }
      retries = 0;
      onMessage?.(ev);
    };

    source.addEventListener("error", (ev) => {
      const miss = parseSsePeelMiss(ev as MessageEvent);
      if (!miss) return;
      closeAfterPeelMiss(miss);
    });

    if (onEvent) {
      for (const [name, handler] of Object.entries(onEvent)) {
        if (typeof handler !== "function" || name === "error") continue;
        source.addEventListener(name, (ev) => {
          const miss = parseSsePeelMiss(ev as MessageEvent);
          if (miss) {
            closeAfterPeelMiss(miss);
            return;
          }
          retries = 0;
          handler(ev as MessageEvent);
        });
      }
    }

    source.onerror = () => {
      source?.close();
      if (closed) return;
      retries += 1;
      onError?.(retries);
      if (retries > maxRetries) {
        if (brokerBacked) {
          onPeelMiss?.({
            via: "broker_miss",
            feature,
            error: terminalFailureMessage,
            status: "degraded",
          });
        }
        onTerminalFailure?.(retries);
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
      source?.close();
    },
  };
}

export { parseSseJson, parseSsePeelMiss };
