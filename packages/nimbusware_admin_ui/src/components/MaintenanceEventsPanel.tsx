import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

export function MaintenanceEventsPanel({ campaignId }: { campaignId: string }) {
  const [events, setEvents] = useState<string[]>([]);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    apiJson<{ maintenance_events?: string[] }>(`/campaigns/${campaignId}/progress`)
      .then((body) => {
        setEvents(body.maintenance_events || []);
        setMsg("");
      })
      .catch((e) => {
        setEvents([]);
        setMsg(String((e as Error).message || e));
      });
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load]);

  if (msg && !events.length) {
    return <p class="muted">{msg}</p>;
  }
  if (!events.length) {
    return <p class="muted">No maintenance events yet.</p>;
  }

  return (
    <div>
      <button type="button" class="secondary" onClick={load}>
        Refresh
      </button>
      <ul>
        {events.map((ev, i) => (
          <li key={`${ev}-${i}`}>{ev}</li>
        ))}
      </ul>
    </div>
  );
}
