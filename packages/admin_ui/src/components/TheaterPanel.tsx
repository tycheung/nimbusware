import { useEffect, useState } from "preact/hooks";
import { apiBase, apiJson } from "../api/client";

type TheaterMessage = {
  store_seq?: number;
  headline?: string;
  body_md?: string | null;
  evidence_refs?: string[];
};

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

  useEffect(() => {
    setErr("");
    apiJson<{ messages?: TheaterMessage[] }>(`/runs/${runId}/theater?limit=200`)
      .then((body) => setMessages(body.messages || []))
      .catch((e) => {
        setMessages([]);
        setErr(String((e as Error).message || e));
      });
  }, [runId]);

  if (err) return <p class="hint">{err}</p>;
  if (!messages.length) return <p>No theater messages yet.</p>;

  return (
    <section class="theater-panel">
      <p>
        <a href={`${apiBase()}/runs/${runId}/theater/export`} download>
          Download transcript
        </a>
      </p>
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
