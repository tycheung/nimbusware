import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

export function RunDetailPage({ id }: { id?: string }) {
  const [run, setRun] = useState<Record<string, unknown> | null>(null);
  const [timeline, setTimeline] = useState<unknown>(null);

  useEffect(() => {
    if (!id) return;
    apiJson<Record<string, unknown>>(`/runs/${id}`).then(setRun);
    apiJson(`/runs/${id}/timeline`).then(setTimeline).catch(() => setTimeline(null));
  }, [id]);

  if (!id) return <p>Select a run.</p>;
  if (!run) return <p>Loading run…</p>;

  return (
    <section>
      <h2>Run {id}</h2>
      <pre class="json-block">{JSON.stringify(run, null, 2)}</pre>
      <h3>Timeline</h3>
      <pre class="json-block">{JSON.stringify(timeline, null, 2)}</pre>
      <p>
        <a href={`/v1/maker/app/#/review?run_id=${id}`} target="_blank" rel="noopener">
          Open in Maker review
        </a>
      </p>
    </section>
  );
}
