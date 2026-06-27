export {
  renderLaunchScorecard,
  scorecardFromTimeline,
  fetchScorecardForRun,
} from "../../../nimbusware_ui_shared/js/launch-scorecard.js";

const SURFACE_LAUNCH_ROWS = [
  ["API", "dev_env_http_regression_passed"],
  ["Web", "dev_env_ui_regression_passed"],
  ["E2E", "slice_e2e_passed"],
];

export function renderSurfaceLaunchSummary(container, scorecard) {
  if (!container || !scorecard) return;
  const existing = container.querySelector("[data-testid='maker-surface-launch-summary']");
  if (existing) existing.remove();
  const rows = SURFACE_LAUNCH_ROWS.filter(([, key]) => scorecard[key] != null);
  if (!rows.length) return;
  const wrap = document.createElement("div");
  wrap.className = "surface-launch-summary";
  wrap.dataset.testid = "maker-surface-launch-summary";
  for (const [label, key] of rows) {
    const chip = document.createElement("span");
    const passed = !!scorecard[key];
    chip.className = `surface-launch-chip surface-launch-chip--${passed ? "passed" : "failed"}`;
    chip.dataset.testid = `maker-surface-launch-${label.toLowerCase()}`;
    chip.textContent = `${label}: ${passed ? "passed" : "needs work"}`;
    wrap.appendChild(chip);
  }
  container.prepend(wrap);
}
