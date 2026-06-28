import { apiJson } from "../api-client.js";

export async function mountEnterpriseGovernancePanel(root) {
  const panel = root.querySelector("#enterprise-home-panel");
  const mount = root.querySelector("#enterprise-governance-mount");
  if (!panel || !mount) return;
  try {
    const gov = await apiJson("/platform/fleet-governance");
    mount.replaceChildren();
    const card = document.createElement("article");
    card.className = "panel";
    card.dataset.testid = "maker-home-fleet-governance";
    const title = document.createElement("h4");
    title.textContent = "Fleet governance";
    card.appendChild(title);
    const lines = [
      `Bundle: ${gov.setup_bundle || "default"}`,
      `Mandatory discovery: ${gov.mandatory_discovery ? "yes" : "no"}`,
      `Default surfaces: ${(gov.default_surfaces || []).join(", ")}`,
    ];
    const enforcement = gov.enforcement_policy || {};
    if (enforcement.min_enforcement_level != null) {
      lines.push(
        `Enforcement depth: ${enforcement.min_enforcement_level}–${enforcement.max_enforcement_level}`,
      );
    }
    if (gov.deploy_chain_required) {
      lines.push("Deploy chain: required for enterprise tenants");
    }
    const body = document.createElement("p");
    body.className = "muted";
    body.textContent = lines.join(" · ");
    card.appendChild(body);
    const targets = Array.isArray(gov.allowed_deploy_targets) ? gov.allowed_deploy_targets : [];
    if (targets.length) {
      const allow = document.createElement("p");
      allow.className = "muted";
      allow.dataset.testid = "maker-home-deploy-allowlist";
      allow.textContent = `Allowed deploy targets: ${targets.join(", ")}`;
      card.appendChild(allow);
    }
    const required = Array.isArray(gov.discovery_required_fields)
      ? gov.discovery_required_fields
      : [];
    if (required.length) {
      const req = document.createElement("p");
      req.className = "muted";
      req.dataset.testid = "maker-home-discovery-required";
      req.textContent = `Required discovery fields: ${required.join(", ")}`;
      card.appendChild(req);
    }
    mount.appendChild(card);
  } catch {
    mount.replaceChildren();
  }
}
