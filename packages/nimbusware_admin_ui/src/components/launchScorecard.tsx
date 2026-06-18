export type LaunchScorecard = {
  aggregate?: number;
  maturity?: number;
  maintainability?: number;
  scalability?: number;
  security?: number;
  testability?: number;
  passed?: boolean;
  findings?: string[];
  llm_findings?: string[];
  llm_dimensions?: Record<string, number>;
  dev_env_live_regression_passed?: boolean;
  dev_env_http_regression_passed?: boolean;
  dev_env_ui_regression_passed?: boolean;
  slice_e2e_passed?: boolean;
  put_ui_flow_id?: string;
  dev_env_ui_failed_step?: number | string;
  dev_env_ui_failed_locator?: string;
};

const DIMENSIONS: [string, keyof LaunchScorecard][] = [
  ["aggregate", "aggregate"],
  ["maturity", "maturity"],
  ["maintainability", "maintainability"],
  ["scalability", "scalability"],
  ["security", "security"],
  ["testability", "testability"],
];

const DEV_ENV_ROWS: [string, keyof LaunchScorecard][] = [
  ["dev_env live regression", "dev_env_live_regression_passed"],
  ["dev_env HTTP regression", "dev_env_http_regression_passed"],
  ["dev_env UI regression", "dev_env_ui_regression_passed"],
  ["slice E2E", "slice_e2e_passed"],
];

export function scorecardFromTimeline(
  timeline: Record<string, unknown> | null,
): LaunchScorecard | null {
  const events = (timeline?.events as Array<Record<string, unknown>>) || [];
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (ev.event_type !== "stage.passed") continue;
    const payload = (ev.payload as Record<string, unknown>) || {};
    if (payload.stage_name !== "launch_eval.completed") continue;
    return (ev.metadata as LaunchScorecard) || (payload as LaunchScorecard);
  }
  return null;
}

export function LaunchScorecardBody({
  scorecard,
  testIdPrefix = "admin",
}: {
  scorecard: LaunchScorecard;
  testIdPrefix?: string;
}) {
  const findings = scorecard.findings?.length ? scorecard.findings : scorecard.llm_findings;

  return (
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
        <p data-testid={`${testIdPrefix}-launch-scorecard-status`}>
          {scorecard.passed ? "passed" : "needs work"}
        </p>
      ) : null}
      {DEV_ENV_ROWS.map(([label, key]) => {
        const value = scorecard[key];
        if (value == null) return null;
        return (
          <p key={key} data-testid={`${testIdPrefix}-launch-scorecard-${key}`}>
            {label}: {value ? "passed" : "failed"}
          </p>
        );
      })}
      {scorecard.put_ui_flow_id ? (
        <p data-testid={`${testIdPrefix}-launch-scorecard-put_ui_flow_id`}>
          UI flow: {scorecard.put_ui_flow_id}
        </p>
      ) : null}
      {scorecard.dev_env_ui_failed_step != null || scorecard.dev_env_ui_failed_locator ? (
        <p data-testid={`${testIdPrefix}-launch-scorecard-ui-flow-failure`}>
          UI flow failure:{" "}
          {[
            scorecard.dev_env_ui_failed_step != null
              ? `step ${scorecard.dev_env_ui_failed_step}`
              : null,
            scorecard.dev_env_ui_failed_locator || null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      ) : null}
      {scorecard.llm_dimensions && Object.keys(scorecard.llm_dimensions).length ? (
        <>
          <h4>LLM dimensions</h4>
          <table class="data-table" data-testid={`${testIdPrefix}-launch-llm-dimensions`}>
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
          <ul data-testid={`${testIdPrefix}-launch-scorecard-findings`}>
            {findings.slice(0, 8).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}
