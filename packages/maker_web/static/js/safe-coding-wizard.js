import { apiJson, toast } from "./api-client.js";
import { formatDomainMissMessage, toastIfMiss } from "./broker_miss.js"; // sak500-b
import { isSafeCodingUx } from "./safe-coding-ux.js";

const WIZARD_DISMISSED_KEY = "maker_safe_coding_wizard_done";
const BOOTSTRAP_POLL_MS = 2500;

export function safeCodingWizardDismissed() {
  return localStorage.getItem(WIZARD_DISMISSED_KEY) === "1";
}

function workspacePathFromProjects(projects) {
  const first = (projects?.projects || projects || [])[0];
  return first?.workspace_path?.trim() || "";
}

async function pollPlaywrightBootstrap(statusEl) {
  for (let i = 0; i < 120; i += 1) {
    const body = await apiJson("/platform/playwright-bootstrap").catch((e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "playwright_bootstrap",
    }));
    if (toastIfMiss(body, toast, "Playwright bootstrap unavailable")) {
      throw new Error(
        formatDomainMissMessage(body, "Playwright bootstrap unavailable") ||
          "Playwright bootstrap unavailable",
      );
    }
    const status = String(body.status || "");
    if (body.plain_summary) statusEl.textContent = body.plain_summary;
    if (status === "ready") return body;
    if (status === "error") throw new Error(body.plain_summary || "Playwright install failed");
    await new Promise((resolve) => setTimeout(resolve, BOOTSTRAP_POLL_MS));
  }
  throw new Error("Browser check install timed out — try again from Home.");
}

export async function mountSafeCodingWizard(root) {
  if (!isSafeCodingUx() || safeCodingWizardDismissed()) return null;
  const host = root.querySelector("#safe-coding-wizard-mount");
  if (!host) return null;

  let workspacePath = "";
  try {
    const listing = await apiJson("/projects");
    workspacePath = workspacePathFromProjects(listing);
  } catch (e) {
    toast(String(e.message || e), "error");
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
      <a href="#/chat?intent=campaign" class="secondary" data-testid="maker-safe-coding-start-campaign" hidden>
        Build full-stack app
      </a>
      <button type="button" class="linkish" data-testid="maker-safe-coding-wizard-skip">Skip for now</button>
    </div>`;
  host.appendChild(panel);

  const statusEl = panel.querySelector("[data-testid='maker-safe-coding-wizard-status']");
  const prepareBtn = panel.querySelector("[data-testid='maker-safe-coding-prepare']");
  const campaignLink = panel.querySelector("[data-testid='maker-safe-coding-start-campaign']");
  const skipBtn = panel.querySelector("[data-testid='maker-safe-coding-wizard-skip']");

  async function refreshReadiness() {
    if (!workspacePath) {
      statusEl.textContent = "Create a project with a workspace path to continue.";
      return;
    }
    try {
      const body = await apiJson(
        `/platform/workspace-readiness?workspace_path=${encodeURIComponent(workspacePath)}`,
      ).catch((e) => ({
        via: "broker_miss",
        error: String(e.message || e),
        feature: "workspace_readiness",
      }));
      if (toastIfMiss(body, toast, "Workspace readiness unavailable")) {
        statusEl.textContent =
          formatDomainMissMessage(body, "Workspace readiness unavailable") ||
          "Workspace readiness unavailable";
        return;
      }
      statusEl.textContent = body.plain_summary || (body.ready ? "Ready to start." : "Needs preparation.");
      const needsWork = (body.warnings || []).length > 0 || !body.checks?.e2e_dir;
      prepareBtn.hidden = !needsWork;
      if (campaignLink) campaignLink.hidden = needsWork;
    } catch (e) {
      const missBody = {
        via: "broker_miss",
        error: String(e.message || e),
        feature: "workspace_readiness",
      };
      toastIfMiss(missBody, toast, "Workspace readiness unavailable");
      statusEl.textContent =
        formatDomainMissMessage(missBody, "Workspace readiness unavailable") ||
        "Workspace readiness unavailable";
    }
  }

  prepareBtn?.addEventListener("click", async () => {
    if (!workspacePath) {
      statusEl.textContent = "Create a project with a workspace path to continue.";
      return;
    }
    prepareBtn.disabled = true;
    skipBtn.disabled = true;
    statusEl.textContent = "Preparing workspace…";
    try {
      const scaffold = await apiJson("/platform/workspace-scaffold", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath }),
      });
      if (toastIfMiss(scaffold, toast, "Workspace scaffold unavailable")) {
        statusEl.textContent =
          formatDomainMissMessage(scaffold, "Workspace scaffold unavailable") ||
          "Workspace scaffold unavailable";
        return;
      }
      const precommit = await apiJson("/platform/workspace-precommit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_path: workspacePath }),
      });
      if (toastIfMiss(precommit, toast, "Workspace precommit unavailable")) {
        statusEl.textContent =
          formatDomainMissMessage(precommit, "Workspace precommit unavailable") ||
          "Workspace precommit unavailable";
        return;
      }
      const bootStart = await apiJson("/platform/playwright-bootstrap", { method: "POST" });
      if (toastIfMiss(bootStart, toast, "Playwright bootstrap unavailable")) {
        statusEl.textContent =
          formatDomainMissMessage(bootStart, "Playwright bootstrap unavailable") ||
          "Playwright bootstrap unavailable";
        return;
      }
      const boot = await pollPlaywrightBootstrap(statusEl);
      statusEl.textContent = boot.plain_summary || "Workspace prepared.";
      localStorage.setItem(WIZARD_DISMISSED_KEY, "1");
      prepareBtn.hidden = true;
      toast("Workspace prepared", "success");
    } catch (e) {
      statusEl.textContent = String(e.message || e);
      toast(String(e.message || e), "error");
    } finally {
      prepareBtn.disabled = false;
      skipBtn.disabled = false;
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
  } catch (e) {
    toast(String(e.message || e), "error");
    return;
  }
  if (!workspacePath) return;
  try {
    const body = await apiJson(
      `/platform/workspace-readiness?workspace_path=${encodeURIComponent(workspacePath)}`,
    ).catch((e) => ({
      via: "broker_miss",
      error: String(e.message || e),
      feature: "workspace_readiness",
    }));
    if (toastIfMiss(body, toast, "Workspace readiness unavailable")) {
      host.replaceChildren();
      const chip = document.createElement("p");
      chip.className = "safe-coding-ribbon muted";
      chip.dataset.testid = "maker-safe-coding-readiness-ribbon";
      chip.textContent =
        formatDomainMissMessage(body, "Workspace readiness unavailable") ||
        "Workspace readiness unavailable";
      host.appendChild(chip);
      return;
    }
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
  } catch (e) {
    host.replaceChildren();
    const chip = document.createElement("p");
    chip.className = "safe-coding-ribbon muted";
    chip.dataset.testid = "maker-safe-coding-readiness-ribbon";
    chip.textContent = String(e.message || e);
    host.appendChild(chip);
    toast(String(e.message || e), "error");
  }
}
