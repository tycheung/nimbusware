import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type ReliabilityRow = { metric: string; value: string };

export function CriticReliabilityPanel({ runId }: { runId: string }) {
  const [caption, setCaption] = useState("");
  const [rows, setRows] = useState<ReliabilityRow[]>([]);

  useEffect(() => {
    apiJson<{ caption?: string; rows?: ReliabilityRow[] }>(
      `/admin/ui/runs/${runId}/critic-reliability`,
    )
      .then((body) => {
        setCaption(body.caption || "");
        setRows(body.rows || []);
      })
      .catch(() => {
        setCaption("");
        setRows([]);
      });
  }, [runId]);

  if (!rows.length) {
    return <p class="muted">{caption || "No critic reliability data."}</p>;
  }

  return (
    <div>
      {caption ? <p>{caption}</p> : null}
      <table class="data-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td>{row.metric}</td>
              <td>{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
