import { scorecardFromTimeline as scorecardFromTimelineShared } from "@nimbusware/ui-shared/js/launch-scorecard.js";

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

export function scorecardFromTimeline(
  timeline: Record<string, unknown> | null,
): LaunchScorecard | null {
  return scorecardFromTimelineShared(timeline) as LaunchScorecard | null;
}

export { LaunchScorecardBody } from "./launchScorecardBody";
