import { apiJson, toast } from "./api-client.js";
import { isSafeCodingUx } from "./safe-coding-ux.js";

const WIZARD_DISMISSED_KEY = "maker_safe_coding_wizard_done";

export function safeCodingWizardDismissed() {
  return localStorage.getItem(WIZARD_DISMISSED_KEY) === "1";
}

function workspacePathFromProjects(projects) {
  const first = (projects?.projects || projects || [])[0];
  return first?.workspace_path?.trim() || "";
}

export async function mountSafeCodingWizard(root) {
  if (!isSafeCodingUx() || safeCodingWizardDismissed()) return null;
  const host = root.querySelector("#safe-coding-wizard-mount");
  if (!host) return null;

  let workspacePath = "";
  try {
    const listing = await apiJson("/projects");
    workspacePath = workspacePathFromProjects(listing);
  } catch {
    /* optional */
  }
  if (!workspacePath) {
    workspacePath = window.__NIMBUSWARE__?.workspace_path || "";
  }

  host.replaceChildren();
  const panel = document.createElement("section");
  panel.className = "panel safe-coding-wizard";
  panel.dataset.testid = "maker-safe-coding-wizard";
  panel.innerHTML = `
    <h3>Prepare your workspace</h3>
    <p class="muted">Safe Coding adds tests and checks so gates can protect your project — no terminal needed.</p>
    <p data-testid="maker-safe-coding-wizard-status" class="muted">Checking workspace…</p>
    <div class="actions">
      <button type="button" class="primary" data-testid="maker-safe-coding-prepare" hidden>Prepare workspace</button>
      <button type="button" class="linkish" data-testid="maker-safe-coding-wizard-skip">Skip for now</button>
    </div>`;
  host.appendChild(panel);

  const statusEl = panel.querySelector("[data-testid='maker-safe-coding-wizard-status']");
  const prepareBtn = panel.querySelector("[data-testid='maker-safe-coding-prepare']");
  const skipBtn = panel.querySelector("[data-testid='maker-safe-coding-wizard-skip']");

  async function refreshReadiness() {
    if (!workspacePath) {
      statusEl.textContent = "Create a project with a workspace path to continue.";
      return;
    }
    try {
      const body = await apiJson(
        `/platform/workspace-readiness?workspace_path=${encodeURIComponent(workspacePath)}`,
      );
      statusEl.textContent = body.plain_summary || (body.ready ? "Ready to start." : "Needs preparation.");
      const needsWork = (body.warnings || []).length > 0 || !body.checks?.e2e_dir;
      prepareBtn.hidden = !needsWork;
    } catch (e) {
      statusEl.textContent = String(e.message || e);
    }
  }

  prepareBtn?.addEventListener("click", async () => {
    if (!workspacePath) return;
    prepareBtn.disabled = true;
    statusEl.textContent = "Preparing workspace…";
    try {
      await apiJson("/platform/workspace-scaffold", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath }),
      });
      await apiJson("/platform/workspace-precommit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath }),
      });
      const boot = await apiJson("/platform/playwright-bootstrap", { method: "POST" });
      statusEl.textContent = boot.plain_summary || "Workspace prepared.";
      localStorage.setItem(WIZARD_DISMISSED_KEY, "1");
      prepareBtn.hidden = true;
      toast("Workspace prepared", "success");
    } catch (e) {
      statusEl.textContent = String(e.message || e);
      toast(String(e.message || e), "error");
    } finally {
      prepareBtn.disabled = false;
    }
  });

  skipBtn?.addEventListener("click", () => {
    localStorage.setItem(WIZARD_DISMISSED_KEY, "1");
    panel.remove();
  });

  await refreshReadiness();
  return panel;
}

export async function mountSafeCodingReadinessRibbon(root) {
  if (!isSafeCodingUx()) return;
  const host = root.querySelector("#safe-coding-ribbon-mount");
  if (!host) return;
  let workspacePath = "";
  try {
    const listing = await apiJson("/projects");
    workspacePath = workspacePathFromProjects(listing);
  } catch {
    return;
  }
  if (!workspacePath) return;
  try {
    const body = await apiJson(
      `/platform/workspace-readiness?workspace_path=${encodeURIComponent(workspacePath)}`,
    );
    host.replaceChildren();
    const chip = document.createElement("p");
    chip.className = "safe-coding-ribbon muted";
    chip.dataset.testid = "maker-safe-coding-readiness-ribbon";
    const warn = (body.warnings || []).length > 0;
    chip.textContent = body.plain_summary || (body.ready ? "Workspace ready" : "Workspace needs attention");
    if (warn) {
      const link = document.createElement("button");
      link.type = "button";
      link.className = "linkish";
      link.textContent = "Open wizard";
      link.addEventListener("click", () => {
        localStorage.removeItem(WIZARD_DISMISSED_KEY);
        mountSafeCodingWizard(root);
      });
      chip.append(" · ");
      chip.appendChild(link);
    }
    host.appendChild(chip);
  } catch {
    host.replaceChildren();
  }
}
