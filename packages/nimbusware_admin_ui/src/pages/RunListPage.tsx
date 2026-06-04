import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type RunRow = { run_id: string; status?: string; workflow_profile?: string };

export function RunListPage() {
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ runs?: RunRow[]; items?: RunRow[] }>("/runs?limit=50")
      .then((body) => setRuns(body.runs || body.items || []))
      .catch((e) => setError(String(e.message || e)));
  }, []);

  if (error) return <p class="error">{error}</p>;

  return (
    <section>
      <h2>Runs</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Status</th>
            <th>Workflow</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.run_id}>
              <td>
                <a href={`/v1/admin/app/runs/${r.run_id}`}>{r.run_id}</a>
              </td>
              <td>{r.status || "—"}</td>
              <td>{r.workflow_profile || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
