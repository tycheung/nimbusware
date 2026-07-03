export function contractGateFromTimeline(events) {
  let state = "pending";
  let detail = "Contract gate not run yet";
  for (const ev of events || []) {
    if (ev.event_type !== "stage.passed" && ev.event_type !== "stage.failed") continue;
    const stage = String(ev.payload?.stage_name || "");
    if (stage !== "slice.contract") continue;
    state = ev.event_type === "stage.passed" ? "passed" : "failed";
    detail =
      ev.metadata?.detail ||
      ev.payload?.detail ||
      ev.payload?.message ||
      (state === "passed" ? "Contract artifacts verified" : "Contract check failed");
    break;
  }
  return { state, detail };
}

export function contractGateCardHtml(gate, { testIdPrefix = "maker-plan" } = {}) {
  const state = gate?.state || "pending";
  const detail = gate?.detail || "";
  return `<section class="plan-contract-gate panel" data-testid="${testIdPrefix}-contract-gate" data-state="${state}">
    <h4>Contract gate</h4>
    <p class="plan-contract-status" data-testid="${testIdPrefix}-contract-status">${state}</p>
    ${detail ? `<p class="muted plan-contract-detail" data-testid="${testIdPrefix}-contract-detail">${detail}</p>` : ""}
  </section>`;
}
