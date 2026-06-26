import { resolveRunId } from "../../session-hub.js";
import { isSafeCodingUx } from "../../safe-coding-ux.js";

export function renderWorkType(body) {
  const badge = document.getElementById("work-type-badge");
  if (!badge) return;
  const wt = String(body.work_type || "").trim().toLowerCase();
  if (!wt) {
    badge.hidden = true;
    badge.textContent = "";
    badge.dataset.workType = "";
    return;
  }
  badge.hidden = false;
  badge.dataset.workType = wt;
  badge.textContent = `Work type: ${wt}`;
}

export function renderEnforcementStatus(body) {
  const chip = document.getElementById("enforcement-chip");
  if (!chip) return;
  const bundle = window.__NIMBUSWARE__?.setup_bundle || "";
  if (bundle === "enterprise") {
    chip.hidden = false;
    chip.dataset.testid = "maker-enterprise-strict-chips";
    chip.textContent =
      "Enterprise strict · platform_grade · tiny slices · auto-commit · audit retention";
    return;
  }
  const es = body.enforcement_status;
  if (!es || es.level == null) {
    chip.hidden = true;
    chip.textContent = "";
    return;
  }
  chip.hidden = false;
  const gate =
    es.gate_passed === true ? " · terminal gate pass" : es.gate_passed === false ? " · terminal gate fail" : "";
  chip.textContent = `Enforcement ${es.level} · ${es.name || "Custom"}${gate}`;
}

export function renderFactoryStatus(body) {
  const chip = document.getElementById("factory-status-chip");
  if (!chip) return;
  if (isSafeCodingUx()) {
    chip.hidden = true;
    chip.textContent = "";
    return;
  }
  const fs = body.factory_status;
  if (!fs || !fs.tier) {
    chip.hidden = true;
    chip.textContent = "";
    return;
  }
  chip.hidden = false;
  const ism = fs.ism_coverage_pct != null ? ` · ISM ${Math.round(fs.ism_coverage_pct)}%` : "";
  const put = fs.put_e2e_passed == null ? "" : fs.put_e2e_passed ? " · PUT E2E pass" : " · PUT E2E fail";
  chip.replaceChildren();
  chip.appendChild(document.createTextNode(`Factory ${fs.tier}${ism}${put}`));
  const promo = fs.tier_promotion?.remaining_gates;
  if (Array.isArray(promo) && promo.length) {
    const promoSpan = document.createElement("span");
    promoSpan.className = "muted";
    promoSpan.dataset.testid = "maker-factory-tier-promotion";
    promoSpan.textContent = ` · Next: ${promo[0]}`;
    chip.appendChild(promoSpan);
  }
  const rid = resolveRunId();
  if (rid) {
    const link = document.createElement("a");
    link.href = `/v1/runs/${encodeURIComponent(rid)}/factory-evidence/export`;
    link.textContent = " · Download evidence";
    link.setAttribute("download", `factory-evidence-${rid}.zip`);
    link.dataset.testid = "maker-factory-evidence-download";
    chip.appendChild(link);
  }
}
