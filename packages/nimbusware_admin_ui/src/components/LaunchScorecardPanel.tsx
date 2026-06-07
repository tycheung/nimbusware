import { useCallback, useState } from "preact/hooks";
import { apiJson } from "../api/client";
import { type LaunchScorecard, scorecardFromTimeline } from "./launchScorecard";

const DIMENSIONS: [string, keyof LaunchScorecard][] = [
  ["aggregate", "aggregate"],
  ["maturity", "maturity"],
  ["maintainability", "maintainability"],
  ["scalability", "scalability"],
  ["security", "security"],
  ["testability", "testability"],
];

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

  const findings = scorecard?.findings?.length
    ? scorecard.findings
    : scorecard?.llm_findings;

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
        <>
          <table class="data-table">
            <tbody>
              {DIMENSIONS.map(([label, key]) => {
                const value = scorecard[key];
                if (value == null || typeof value === "boolean") return null;
                return (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    <td>{String(value)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {scorecard.passed != null ? (
            <p data-testid="admin-launch-scorecard-status">{scorecard.passed ? "passed" : "needs work"}</p>
          ) : null}
          {scorecard.llm_dimensions && Object.keys(scorecard.llm_dimensions).length ? (
            <>
              <h4>LLM dimensions</h4>
              <table class="data-table" data-testid="admin-launch-llm-dimensions">
                <tbody>
                  {Object.entries(scorecard.llm_dimensions).map(([key, val]) => (
                    <tr key={key}>
                      <th scope="row">{key}</th>
                      <td>{val}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
          {findings?.length ? (
            <>
              <h4>Findings</h4>
              <ul data-testid="admin-launch-scorecard-findings">
                {findings.slice(0, 8).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
