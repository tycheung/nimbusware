import { useCampaignProgress } from "../context/CampaignProgressContext";
import { PanelFrame } from "./PanelFrame";

export function MaintenanceEventsPanel() {
  const { body, error, reload } = useCampaignProgress();
  const events = body?.maintenance_events || [];

  return (
    <PanelFrame
      error={error}
      empty={!events.length}
      emptyMessage="No maintenance events yet."
      onRefresh={reload}
    >
      <ul>
        {events.map((ev, i) => (
          <li key={`${ev}-${i}`}>{ev}</li>
        ))}
      </ul>
    </PanelFrame>
  );
}
