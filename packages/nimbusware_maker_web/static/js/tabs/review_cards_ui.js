export function renderPendingCards(body, container) {
  container.replaceChildren();

  const statusCard = document.createElement("article");
  statusCard.className = "approval-card approval-card--status";
  statusCard.dataset.testid = "maker-review-status-card";

  const planLine = document.createElement("p");
  planLine.dataset.testid = "maker-review-plan-status";
  planLine.textContent = body.plan_approved ? "Plan: approved" : "Plan: awaiting approval";
  statusCard.appendChild(planLine);

  const sliceLine = document.createElement("p");
  sliceLine.dataset.testid = "maker-review-slice-status";
  sliceLine.textContent = body.awaiting_approval
    ? "Slice: awaiting your approval"
    : "Slice: no pending approval";
  statusCard.appendChild(sliceLine);
  container.appendChild(statusCard);

  if (body.pending) {
    const p = body.pending;
    const card = document.createElement("article");
    card.className = "approval-card approval-card--pending";
    card.dataset.testid = "maker-review-pending-card";

    const title = document.createElement("h4");
    title.textContent = `Slice ${p.slice_id || p.id || "pending"}`;
    card.appendChild(title);

    if (p.slice_index != null && p.slice_total != null) {
      const prog = document.createElement("p");
      prog.className = "muted";
      prog.textContent = `Progress: ${Number(p.slice_index) + 1}/${p.slice_total}`;
      card.appendChild(prog);
    }

    if (p.rationale) {
      const rat = document.createElement("p");
      rat.className = "approval-rationale";
      rat.dataset.testid = "maker-review-pending-rationale";
      rat.textContent = p.rationale;
      card.appendChild(rat);
    }

    if (p.gate_verdict === "FAIL" || p.last_gate_fail) {
      const gate = document.createElement("p");
      gate.className = "approval-gate-fail gate-summary-banner";
      gate.dataset.testid = "maker-review-pending-gate-fail";
      gate.textContent = p.last_gate_fail || "Previous slice gate failed — review before apply.";
      card.appendChild(gate);
    }

    if (Array.isArray(p.target_paths) && p.target_paths.length) {
      const paths = document.createElement("ul");
      paths.className = "approval-target-paths";
      paths.dataset.testid = "maker-review-pending-paths";
      for (const tp of p.target_paths.slice(0, 8)) {
        const li = document.createElement("li");
        li.textContent = String(tp);
        paths.appendChild(li);
      }
      card.appendChild(paths);
    }

    const mode = document.createElement("p");
    mode.className = "muted";
    mode.textContent = `Implement mode: ${p.implement_mode || "scoped"}`;
    card.appendChild(mode);

    container.appendChild(card);
  }

  if (body.last_snapshot) {
    const snap = document.createElement("article");
    snap.className = "approval-card approval-card--snapshot";
    snap.dataset.testid = "maker-review-last-snapshot";
    const h = document.createElement("h4");
    h.textContent = "Last applied snapshot";
    snap.appendChild(h);
    const pre = document.createElement("pre");
    pre.className = "json-pre";
    pre.textContent = JSON.stringify(body.last_snapshot, null, 2);
    snap.appendChild(pre);
    container.appendChild(snap);
  }
}
