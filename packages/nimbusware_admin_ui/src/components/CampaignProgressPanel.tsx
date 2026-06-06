import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type CampaignProgress = {
  state?: string;
  autonomous?: boolean;
  current_slice_id?: string | null;
  slices_completed?: number;
  slices_total?: number;
  next_maintenance?: {
    refactor_in_slices?: number | null;
    architecture_in_slices?: number | null;
  };
};

export function CampaignProgressPanel({ campaignId }: { campaignId: string }) {
  const [progress, setProgress] = useState<CampaignProgress | null>(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    apiJson<{ progress?: CampaignProgress }>(`/campaigns/${campaignId}/progress`)
      .then((body) => {
        setProgress(body.progress || null);
        setMsg("");
      })
      .catch((e) => {
        setProgress(null);
        setMsg(String((e as Error).message || e));
      });
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load]);

  if (msg && !progress) {
    return <p class="muted">{msg}</p>;
  }
  if (!progress) {
    return <p class="muted">No campaign progress.</p>;
  }

  return (
    <div>
      <button type="button" class="secondary" onClick={load}>
        Refresh
      </button>
      <dl class="kv">
        <dt>State</dt>
        <dd>{progress.state || "—"}</dd>
        <dt>Autonomous</dt>
        <dd>{progress.autonomous ? "yes" : "no"}</dd>
        <dt>Current slice</dt>
        <dd>{progress.current_slice_id || "—"}</dd>
        <dt>Slices</dt>
        <dd>
          {progress.slices_completed ?? 0}/{progress.slices_total ?? "?"}
        </dd>
        <dt>Next refactor</dt>
        <dd>{progress.next_maintenance?.refactor_in_slices ?? "—"}</dd>
        <dt>Next architecture</dt>
        <dd>{progress.next_maintenance?.architecture_in_slices ?? "—"}</dd>
      </dl>
    </div>
  );
}
