const GATE_STEP_PLAIN = {
  "slice.verify": "Code checks",
  "slice.critique": "Quality review",
  "slice.test": "Automated tests",
  "slice.e2e": "Browser tests",
  "slice.gate": "Final safety gate",
  launch_test: "Launch test",
};

const CHECKPOINT_PLAIN = {
  stop_after_run_plan: "Pause after run plan",
  stop_after_slice_plan: "Pause after slice plan",
  stop_before_workspace_apply: "Pause before applying changes",
  stop_on_slice_test_fail: "Pause when tests fail",
  stop_on_dev_env_regression_fail: "Pause when live app checks fail",
  stop_on_ui_regression_fail: "Pause when UI checks fail",
  stop_on_gate_fail: "Pause when safety checks fail",
  stop_before_factory_complete: "Pause before factory completes",
  stop_at_terminal_review: "Pause at final review",
};

export const ARCHETYPE_PRESETS = {
  safe_coding: {
    workflow_profile: "safe_coding",
    autopilot_profile_id: "guided",
    enforcement_profile_id: "balanced",
    collab_hint: false,
    label: "Safe Coding",
  },
  engineer: {
    workflow_profile: "micro_slice",
    autopilot_profile_id: "guided",
    enforcement_profile_id: "balanced",
    collab_hint: true,
    label: "Engineer workspace",
  },
};

export function plainGateStepLabel(stepId) {
  const key = String(stepId || "").trim();
  return GATE_STEP_PLAIN[key] || key.replaceAll("_", " ");
}

export function plainCheckpointLabel(checkpointId) {
  const key = String(checkpointId || "").trim();
  return CHECKPOINT_PLAIN[key] || key.replaceAll("_", " ");
}

export function formatPlainGateSummary(raw) {
  if (raw == null) return "";
  if (typeof raw === "string") return raw.trim();
  if (typeof raw !== "object") return String(raw).trim();
  const parts = [];
  for (const [k, v] of Object.entries(raw)) {
    if (v == null || v === "") continue;
    const label = plainGateStepLabel(k);
    const verdict = typeof v === "object" ? v.verdict || v.status || JSON.stringify(v) : String(v);
    const plainVerdict =
      verdict === "PASS"
        ? "passed"
        : verdict === "FAIL"
          ? "failed — review before continuing"
          : verdict === "SKIP"
            ? "skipped"
            : verdict;
    parts.push(`${label}: ${plainVerdict}`);
  }
  return parts.join(" · ");
}
