import { useState } from "preact/hooks";
import { apiJson } from "../api/client";
import { useApiGet } from "../hooks/useApiGet";
import { briefReviewStatus } from "./researchStatus";
import { PanelFrame } from "./PanelFrame";

type ResearchBrief = {
  brief_id?: string;
  artifact_id?: string;
  brief_kind?: string;
  status?: string;
  review_status?: string;
  summary?: string;
};

export function ResearchPanel({ runId }: { runId: string }) {
  const [actionMsg, setActionMsg] = useState("");
  const { data: briefs, error, reload } = useApiGet<ResearchBrief[]>(
    `/runs/${runId}/research`,
    (body) => (body as { briefs?: ResearchBrief[] }).briefs || [],
    [],
  );

  async function review(briefId: string, action: "approve" | "reject") {
    try {
      await apiJson(`/runs/${runId}/research/${encodeURIComponent(briefId)}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: "" }),
      });
      setActionMsg("");
      reload();
    } catch (e) {
      setActionMsg(String((e as Error).message || e));
    }
  }

  return (
    <PanelFrame
      error={error || actionMsg}
      empty={!briefs.length}
      emptyMessage="No research briefs for this run."
      onRefresh={reload}
    >
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
            const status = briefReviewStatus(brief);
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
    </PanelFrame>
  );
}
