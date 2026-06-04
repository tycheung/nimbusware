import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type Entry = { run_id: string; preflight?: Record<string, unknown> | null };

export function PreflightPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ entries?: Entry[] }>("/preflight-history?limit=20")
      .then((b) => setEntries(b.entries || []))
      .catch((e) => setError(String((e as Error).message || e)));
  }, []);

  return (
    <section>
      <h2>Preflight history</h2>
      <p class="muted">
        Cross-run preflight entries. Fleet Ollama SLI aggregate is on the{" "}
        <a href="/v1/admin/app/fleet">Fleet</a> tab (Enterprise).
      </p>
      {error ? <p class="error">{error}</p> : null}
      <table class="data-table">
        <thead>
          <tr>
            <th>Run</th>
            <th>Workflow</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i}>
              <td>
                {e.run_id ? <a href={`/v1/admin/app/runs/${e.run_id}`}>{e.run_id}</a> : "—"}
              </td>
              <td>{String((e.preflight as Record<string, unknown>)?.workflow_profile || "—")}</td>
              <td>{e.preflight ? "present" : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
