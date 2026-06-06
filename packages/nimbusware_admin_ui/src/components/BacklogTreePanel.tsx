import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type BacklogTree = {
  epics?: {
    epic_id?: string;
    title?: string;
    status?: string;
    features?: {
      feature_id?: string;
      title?: string;
      slices?: { slice_id?: string; status?: string }[];
    }[];
  }[];
  summary?: {
    total_slices?: number;
    slices_completed?: number;
    slices_pending?: number;
  };
};

export function BacklogTreePanel({ campaignId }: { campaignId: string }) {
  const [tree, setTree] = useState<BacklogTree | null>(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    apiJson<{ backlog?: BacklogTree }>(`/campaigns/${campaignId}/progress`)
      .then((body) => {
        setTree(body.backlog || null);
        setMsg("");
      })
      .catch((e) => {
        setTree(null);
        setMsg(String((e as Error).message || e));
      });
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load]);

  if (msg && !tree) {
    return <p class="muted">{msg}</p>;
  }
  if (!tree?.epics?.length) {
    return <p class="muted">No delivery backlog.</p>;
  }

  return (
    <div>
      <button type="button" class="secondary" onClick={load}>
        Refresh
      </button>
      {tree.summary ? (
        <p class="hint">
          {tree.summary.slices_completed ?? 0}/{tree.summary.total_slices ?? "?"} complete,{" "}
          {tree.summary.slices_pending ?? 0} pending
        </p>
      ) : null}
      <ul>
        {tree.epics.map((epic) => (
          <li key={epic.epic_id || epic.title}>
            <strong>{epic.title || epic.epic_id}</strong> ({epic.status || "—"})
            <ul>
              {(epic.features || []).map((feat) => (
                <li key={feat.feature_id || feat.title}>
                  {feat.title || feat.feature_id}
                  <ul>
                    {(feat.slices || []).map((sl) => (
                      <li key={sl.slice_id}>
                        {sl.slice_id}: {sl.status || "—"}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
