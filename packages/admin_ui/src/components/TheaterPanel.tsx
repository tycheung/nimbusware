import { useEffect, useState } from "preact/hooks";

import {
  apiBase,
  adminHeaders,
  apiJson,
  formatPeelMissMessage,
  formatReadCatchMessage,
  isDomainPeelMiss,
  openSseStream,
  parseSseJson,
} from "../api/client"; // sak499-d

type TheaterMessage = {
  store_seq?: number;
  headline?: string;
  body_md?: string | null;
  evidence_refs?: string[];
};

function theaterPayloadFromSse(data: Record<string, unknown>): TheaterMessage | null {
  if (!data || typeof data !== "object") return null;
  if (data.headline || data.body_md) {
    return data as TheaterMessage;
  }
  return null;
}

function appendTheaterFromSse(
  data: Record<string, unknown>,
  setMessages: (fn: (prev: TheaterMessage[]) => TheaterMessage[]) => void,
) {
  if (Array.isArray(data.messages)) {
    for (const row of data.messages) {
      const msg = theaterPayloadFromSse(row as Record<string, unknown>);
      if (msg) {
        setMessages((prev) => {
          const seq = Number(msg.store_seq || 0);
          if (seq && prev.some((m) => Number(m.store_seq || 0) === seq)) return prev;
          return [...prev, msg];
        });
      }
    }
    return;
  }
  const msg = theaterPayloadFromSse(data);
  if (!msg) return;
  setMessages((prev) => {
    const seq = Number(msg.store_seq || 0);
    if (seq && prev.some((m) => Number(m.store_seq || 0) === seq)) return prev;
    return [...prev, msg];
  });
}

async function downloadTheaterExport(runId: string): Promise<string | null> {
  const res = await fetch(`${apiBase()}/runs/${encodeURIComponent(runId)}/theater/export`, {
    headers: adminHeaders(),
  });
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("application/json")) {
    const body = (await res.json()) as { via?: string; error?: string; feature?: string };
    if (isDomainPeelMiss(body)) {
      return formatPeelMissMessage(body, "theater export unavailable");
    }
  }
  if (!res.ok) {
    return formatPeelMissMessage({ error: `HTTP ${res.status}` }, "theater export unavailable");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `nimbusware-theater-${runId}.md`;
  a.click();
  URL.revokeObjectURL(url);
  return null;
}

export function TheaterPanel({
  runId,
  onJumpToSeq,
}: {
  runId: string;
  onJumpToSeq?: (seq: number) => void;
}) {
  const [messages, setMessages] = useState<TheaterMessage[]>([]);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [err, setErr] = useState("");
  const [streamErr, setStreamErr] = useState("");
  const [exportMsg, setExportMsg] = useState("");

  useEffect(() => {
    setErr("");
    setStreamErr("");
    let streamHandle: { close: () => void } | null = null;
    let cancelled = false;

    apiJson<{ messages?: TheaterMessage[]; via?: string; error?: string; status?: string }>(
      `/runs/${runId}/theater?limit=200`,
    )
      .then((body) => {
        if (cancelled) return;
        if (isDomainPeelMiss(body)) {
          setMessages([]);
          setErr(formatPeelMissMessage(body, "theater unavailable"));
          return;
        }
        setMessages(body.messages || []);
        setErr("");

        // sak491-i: live theater SSE with peel miss close (Maker theater stream parity).
        streamHandle = openSseStream(`/runs/${encodeURIComponent(runId)}/theater/stream`, {
          apiBase: apiBase(),
          brokerBacked: true,
          feature: "theater_stream",
          terminalFailureMessage: "Theater stream unavailable",
          onPeelMiss: (miss) => {
            if (!cancelled) {
              setStreamErr(formatPeelMissMessage(miss, "theater stream unavailable"));
            }
          },
          onEvent: {
            theater: (ev) => {
              const data = parseSseJson(ev);
              if (data) appendTheaterFromSse(data, setMessages);
            },
          },
          onMessage: (ev) => {
            const data = parseSseJson(ev);
            if (data) appendTheaterFromSse(data, setMessages);
          },
        });
      })
      .catch((e) => {
        if (cancelled) return;
        setMessages([]);
        setErr(formatReadCatchMessage(e, "theater unavailable"));
      });

    return () => {
      cancelled = true;
      streamHandle?.close();
    };
  }, [runId]);

  const exportControl = (
    <p>
      <button
        type="button"
        class="linkish"
        data-testid="admin-theater-export"
        onClick={() => {
          setExportMsg("");
          void downloadTheaterExport(runId).then((miss) => {
            if (miss) setExportMsg(miss);
          });
        }}
      >
        Download transcript
      </button>
      {exportMsg ? <span class="hint"> — {exportMsg}</span> : null}
    </p>
  );

  if (err) {
    return (
      <section class="theater-panel">
        {exportControl}
        <p class="hint">{err}</p>
      </section>
    );
  }

  if (!messages.length) {
    return (
      <section class="theater-panel">
        {exportControl}
        {streamErr ? <p class="hint">{streamErr}</p> : null}
        <p>No theater messages yet.</p>
      </section>
    );
  }

  return (
    <section class="theater-panel">
      {exportControl}
      {streamErr ? <p class="hint">{streamErr}</p> : null}
      <ul class="theater-list">
        {messages.map((msg) => {
          const seq = Number(msg.store_seq || 0);
          const open = Boolean(expanded[seq]);
          const body = (msg.body_md || "").trim();
          return (
            <li key={seq} data-store-seq={seq}>
              <div class="theater-headline">
                <strong>#{seq}</strong> {msg.headline || "—"}
                {body ? (
                  <button
                    type="button"
                    class="linkish"
                    onClick={() => setExpanded((e) => ({ ...e, [seq]: !open }))}
                  >
                    {open ? "Hide" : "Evidence"}
                  </button>
                ) : null}
                {onJumpToSeq ? (
                  <button type="button" class="linkish" onClick={() => onJumpToSeq(seq)}>
                    Jump to timeline
                  </button>
                ) : null}
              </div>
              {open && body ? <pre class="theater-body">{body}</pre> : null}
              {open && msg.evidence_refs?.length ? (
                <ul class="muted">
                  {msg.evidence_refs.map((ref) => (
                    <li key={ref}>{ref}</li>
                  ))}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
