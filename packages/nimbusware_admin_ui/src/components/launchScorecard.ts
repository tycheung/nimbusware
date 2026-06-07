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
};

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
