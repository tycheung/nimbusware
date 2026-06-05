import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type StitchEvent = {
  store_seq?: number;
  event_type?: string;
  summary?: string;
  payload?: Record<string, unknown>;
};

export function StitchSummaryPanel({ runId }: { runId: string }) {
  const [events, setEvents] = useState<StitchEvent[]>([]);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    apiJson<{ events?: StitchEvent[]; transplant_outcome?: string | null }>(
      `/runs/${runId}/stitch-summary`,
    )
      .then((body) => {
        setEvents(body.events || []);
        setOutcome(body.transplant_outcome ?? null);
        setMsg("");
      })
      .catch((e) => {
        setEvents([]);
        setOutcome(null);
        setMsg(String((e as Error).message || e));
      });
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  if (msg && !events.length) {
    return <p class="muted">{msg}</p>;
  }
  if (!events.length) {
    return <p class="muted">No stitch events for this run.</p>;
  }

  return (
    <div>
      {outcome ? (
        <p>
          Transplant outcome: <strong>{outcome}</strong>
        </p>
      ) : null}
      <button type="button" class="secondary" onClick={load}>
        Refresh
      </button>
      <table class="data-table">
        <thead>
          <tr>
            <th>Seq</th>
            <th>Event</th>
            <th>Summary</th>
            <th>Payload</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev, i) => {
            const seq = ev.store_seq ?? i;
            const open = expanded[seq];
            return (
              <tr key={seq}>
                <td>{seq}</td>
                <td>{ev.event_type || "—"}</td>
                <td>{ev.summary || "—"}</td>
                <td>
                  {ev.payload ? (
                    <button
                      type="button"
                      class="linkish"
                      onClick={() => setExpanded({ ...expanded, [seq]: !open })}
                    >
                      {open ? "Hide" : "Show"}
                    </button>
                  ) : (
                    "—"
                  )}
                  {open && ev.payload ? (
                    <pre class="json-block">{JSON.stringify(ev.payload, null, 2)}</pre>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
