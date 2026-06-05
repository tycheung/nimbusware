import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type IawRow = { field: string; value: string };

export function IntegrationAdapterPanel({ runId }: { runId: string }) {
  const [caption, setCaption] = useState("");
  const [rows, setRows] = useState<IawRow[]>([]);
  const [present, setPresent] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    apiJson<{
      present?: boolean;
      caption?: string;
      rows?: IawRow[];
    }>(`/admin/ui/runs/${runId}/integration-adapter-writer`)
      .then((body) => {
        setPresent(Boolean(body.present));
        setCaption(body.caption || "");
        setRows(body.rows || []);
        setMsg("");
      })
      .catch((e) => {
        setPresent(false);
        setCaption("");
        setRows([]);
        setMsg(String((e as Error).message || e));
      });
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  if (msg) return <p class="muted">{msg}</p>;
  if (!present) return <p class="muted">{caption || "No Integration Adapter Writer stage."}</p>;

  return (
    <div>
      <p>{caption}</p>
      <button type="button" class="secondary" onClick={load}>
        Refresh
      </button>
      {rows.length ? (
        <table class="data-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.field}>
                <td>{row.field}</td>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
