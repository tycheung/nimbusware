import { useCallback, useState } from "preact/hooks";
import { apiJson } from "../api/client";
import { LaunchScorecardBody, scorecardFromTimeline } from "./launchScorecard";

export function LaunchScorecardPanel({
  runId,
  timeline,
  onTimelineRefresh,
}: {
  runId: string;
  timeline: Record<string, unknown> | null;
  onTimelineRefresh: () => Promise<void>;
}) {
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const scorecard = scorecardFromTimeline(timeline);

  const runLaunchCheck = useCallback(async () => {
    setBusy(true);
    setMsg("");
    try {
      await apiJson(`/runs/${runId}/maker/launch-eval`, { method: "POST" });
      await onTimelineRefresh();
      setMsg("Launch check complete.");
    } catch (e) {
      setMsg(String((e as Error).message || e));
    } finally {
      setBusy(false);
    }
  }, [runId, onTimelineRefresh]);

  return (
    <div data-testid="admin-launch-scorecard-panel">
      <div class="actions">
        <button type="button" disabled={busy} onClick={() => void runLaunchCheck()}>
          Run launch check
        </button>
        <button type="button" class="secondary" disabled={busy} onClick={() => void onTimelineRefresh()}>
          Refresh
        </button>
      </div>
      {msg ? <p class="hint">{msg}</p> : null}
      {!scorecard ? (
        <p class="muted">No launch_eval.completed event on this run yet.</p>
      ) : (
        <LaunchScorecardBody scorecard={scorecard} />
      )}
    </div>
  );
}
