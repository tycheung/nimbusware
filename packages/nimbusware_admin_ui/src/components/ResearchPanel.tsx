import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type ResearchBrief = {
  brief_id?: string;
  artifact_id?: string;
  brief_kind?: string;
  status?: string;
  summary?: string;
};

export function ResearchPanel({ runId }: { runId: string }) {
  const [briefs, setBriefs] = useState<ResearchBrief[]>([]);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    apiJson<{ briefs?: ResearchBrief[] }>(`/runs/${runId}/research`)
      .then((body) => {
        setBriefs(body.briefs || []);
        setMsg("");
      })
      .catch((e) => {
        setBriefs([]);
        setMsg(String((e as Error).message || e));
      });
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  async function review(briefId: string, action: "approve" | "reject") {
    try {
      await apiJson(`/runs/${runId}/research/${encodeURIComponent(briefId)}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: "" }),
      });
      load();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  if (msg && !briefs.length) {
    return <p class="muted">{msg}</p>;
  }
  if (!briefs.length) {
    return <p class="muted">No research briefs for this run.</p>;
  }

  return (
    <div>
      <button type="button" class="secondary" onClick={load}>
        Refresh
      </button>
      {msg ? <p class="hint">{msg}</p> : null}
      <table class="data-table">
        <thead>
          <tr>
            <th>Kind</th>
            <th>Brief</th>
            <th>Status</th>
            <th>Summary</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {briefs.map((brief, i) => {
            const bid = brief.brief_id || brief.artifact_id || "";
            const status = brief.status || "unknown";
            return (
              <tr key={bid || i}>
                <td>{brief.brief_kind || "—"}</td>
                <td>{bid || "—"}</td>
                <td>{status}</td>
                <td>{brief.summary || "—"}</td>
                <td>
                  {status === "pending" && bid ? (
                    <span class="actions">
                      <button type="button" onClick={() => review(bid, "approve")}>
                        Approve
                      </button>
                      <button type="button" onClick={() => review(bid, "reject")}>
                        Reject
                      </button>
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
