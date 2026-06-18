import { useState } from "preact/hooks";
import { useApiGet } from "../hooks/useApiGet";
import { PanelFrame } from "./PanelFrame";

type StitchEvent = {
  store_seq?: number;
  event_type?: string;
  summary?: string;
  payload?: Record<string, unknown>;
};

type StitchSummary = {
  events: StitchEvent[];
  outcome: string | null;
};

export function StitchSummaryPanel({ runId }: { runId: string }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const { data, error, reload } = useApiGet<StitchSummary>(
    `/runs/${runId}/stitch-summary`,
    (body) => {
      const raw = body as { events?: StitchEvent[]; transplant_outcome?: string | null };
      return {
        events: raw.events || [],
        outcome: raw.transplant_outcome ?? null,
      };
    },
    { events: [], outcome: null },
  );

  return (
    <PanelFrame
      error={error}
      empty={!data.events.length}
      emptyMessage="No stitch events for this run."
      onRefresh={reload}
    >
      {data.outcome ? (
        <p>
          Transplant outcome: <strong>{data.outcome}</strong>
        </p>
      ) : null}
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
          {data.events.map((ev, i) => {
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
    </PanelFrame>
  );
}
