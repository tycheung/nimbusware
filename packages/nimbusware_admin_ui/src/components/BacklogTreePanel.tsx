import { useCampaignProgress } from "../context/CampaignProgressContext";
import { PanelFrame } from "./PanelFrame";

export function BacklogTreePanel() {
  const { body, error, reload } = useCampaignProgress();
  const tree = body?.backlog;

  return (
    <PanelFrame
      error={error}
      empty={!tree?.epics?.length}
      emptyMessage="No delivery backlog."
      onRefresh={reload}
    >
      {tree?.summary ? (
        <p class="hint">
          {tree.summary.slices_completed ?? 0}/{tree.summary.total_slices ?? "?"} complete,{" "}
          {tree.summary.slices_pending ?? 0} pending
        </p>
      ) : null}
      <ul>
        {(tree?.epics || []).map((epic) => (
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
    </PanelFrame>
  );
}
