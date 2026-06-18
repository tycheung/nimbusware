import { useCampaignProgress } from "../context/CampaignProgressContext";
import { PanelFrame } from "./PanelFrame";

export function CampaignProgressPanel() {
  const { body, error, reload } = useCampaignProgress();
  const progress = body?.progress;

  return (
    <PanelFrame
      error={error}
      empty={!progress}
      emptyMessage="No campaign progress."
      onRefresh={reload}
    >
      <dl class="kv">
        <dt>State</dt>
        <dd>{progress?.state || "—"}</dd>
        <dt>Autonomous</dt>
        <dd>{progress?.autonomous ? "yes" : "no"}</dd>
        <dt>Current slice</dt>
        <dd>{progress?.current_slice_id || "—"}</dd>
        <dt>Slices</dt>
        <dd>
          {progress?.slices_completed ?? 0}/{progress?.slices_total ?? "?"}
        </dd>
        <dt>Next refactor</dt>
        <dd>{progress?.next_maintenance?.refactor_in_slices ?? "—"}</dd>
        <dt>Next architecture</dt>
        <dd>{progress?.next_maintenance?.architecture_in_slices ?? "—"}</dd>
      </dl>
    </PanelFrame>
  );
}
