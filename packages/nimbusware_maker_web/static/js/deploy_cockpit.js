import { apiJson, toast } from "./api-client.js";

const CI_STAGE_PREFIXES = ["ci.", "deploy.", "terraform."];

export function deployStateFromTimeline(events) {
  let ciStatus = "not_started";
  let ciDetail = "No CI workflow events yet";
  let planArtifact = "";
  let deployApproved = false;
  let deployApplied = false;
  let apiUrl = "";
  let webUrl = "";

  for (const ev of events || []) {
    const meta = ev.metadata || {};
    if (!apiUrl && meta.api_url) apiUrl = String(meta.api_url);
    if (!webUrl && meta.web_url) webUrl = String(meta.web_url);
    const urls = meta.live_urls;
    if (urls && typeof urls === "object") {
      if (!apiUrl && urls.api) apiUrl = String(urls.api);
      if (!webUrl && urls.web) webUrl = String(urls.web);
    }
  }

  for (const ev of [...(events || [])].reverse()) {
    const stage = String(ev.payload?.stage_name || "");
    if (!stage) continue;
    const lower = stage.toLowerCase();
    if (lower === "deploy.approved") {
      deployApproved = ev.event_type === "stage.passed";
      continue;
    }
    if (lower === "deploy.apply") {
      deployApplied = ev.event_type === "stage.passed";
      continue;
    }
    if (!CI_STAGE_PREFIXES.some((p) => lower.startsWith(p))) continue;
    if (ev.event_type === "stage.passed") {
      ciStatus = "passed";
      ciDetail = ev.metadata?.detail || ev.payload?.detail || stage;
    } else if (ev.event_type === "stage.failed") {
      ciStatus = "failed";
      ciDetail = ev.metadata?.detail || ev.payload?.detail || stage;
    } else if (ev.event_type === "stage.started" && ciStatus === "not_started") {
      ciStatus = "running";
      ciDetail = stage;
    }
    const artifact = ev.metadata?.plan_artifact || ev.payload?.plan_artifact;
    if (artifact && !planArtifact) planArtifact = String(artifact);
    if (ciStatus !== "not_started") break;
  }

  return { ciStatus, ciDetail, planArtifact, deployApproved, deployApplied, apiUrl, webUrl };
}

export function deployCockpitHtml({ scope = "progress" } = {}) {
  const p = scope === "progress" ? "" : `${scope}-`;
  return `
    <section class="panel deploy-cockpit" data-deploy-scope="${scope}" data-testid="maker-deploy-cockpit-${scope}">
      <h4>Deploy cockpit</h4>
      <p class="muted deploy-cockpit-ci" data-testid="maker-deploy-ci-status-${scope}">CI: not started</p>
      <p class="muted deploy-cockpit-plan" data-testid="maker-deploy-plan-artifact-${scope}" hidden></p>
      <p class="muted deploy-cockpit-urls" data-testid="maker-deploy-live-urls-${scope}" hidden></p>
      <div class="actions">
        <button type="button" class="deploy-validate-btn" data-deploy-scope="${scope}" data-testid="maker-deploy-validate-${scope}">
          Run Terraform validate
        </button>
        <button type="button" class="deploy-approve-btn" data-deploy-scope="${scope}" data-testid="maker-deploy-approve-${scope}" disabled>
          Approve deploy
        </button>
        <button type="button" class="deploy-apply-btn" data-deploy-scope="${scope}" data-testid="maker-deploy-apply-${scope}" disabled>
          Apply deploy
        </button>
        <button type="button" class="deploy-cockpit-refresh" data-deploy-scope="${scope}" data-testid="maker-deploy-refresh-${scope}">Refresh</button>
        <a href="#/settings" data-testid="maker-deploy-settings-link-${scope}">Deploy connections</a>
      </div>
    </section>`;
}

function cockpitRoot(scope) {
  return document.querySelector(`[data-deploy-scope="${scope}"].deploy-cockpit`);
}

export function renderDeployCockpit(state, { scope = "progress" } = {}) {
  const root = cockpitRoot(scope);
  if (!root) return;
  const ciEl = root.querySelector(".deploy-cockpit-ci");
  const planEl = root.querySelector(".deploy-cockpit-plan");
  const urlsEl = root.querySelector(".deploy-cockpit-urls");
  const approveBtn = root.querySelector(".deploy-approve-btn");
  const applyBtn = root.querySelector(".deploy-apply-btn");

  const status = state?.ciStatus || "not_started";
  if (ciEl) {
    ciEl.textContent = `CI: ${status}${state?.ciDetail ? ` — ${state.ciDetail}` : ""}`;
    ciEl.dataset.state = status;
  }

  if (planEl) {
    if (state?.planArtifact) {
      planEl.hidden = false;
      planEl.textContent = `Plan artifact: ${state.planArtifact}`;
    } else {
      planEl.hidden = true;
      planEl.textContent = "";
    }
  }

  if (urlsEl) {
    urlsEl.replaceChildren();
    const links = [];
    if (state?.apiUrl) {
      const a = document.createElement("a");
      a.href = state.apiUrl;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = `API: ${state.apiUrl}`;
      a.dataset.testid = `maker-deploy-live-api-${scope}`;
      links.push(a);
    }
    if (state?.webUrl) {
      const a = document.createElement("a");
      a.href = state.webUrl;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = `Web: ${state.webUrl}`;
      a.dataset.testid = `maker-deploy-live-web-${scope}`;
      links.push(a);
    }
    if (links.length) {
      urlsEl.hidden = false;
      for (let i = 0; i < links.length; i += 1) {
        if (i) urlsEl.append(" · ");
        urlsEl.append(links[i]);
      }
    } else {
      urlsEl.hidden = true;
    }
  }

  if (approveBtn) {
    const canApprove = status === "passed" && state?.planArtifact && !state?.deployApproved;
    approveBtn.disabled = !canApprove;
    approveBtn.title = canApprove
      ? "Record deploy approval for this run"
      : "Requires passing CI plan artifact (configure in Settings → Deploy connections)";
  }
  if (applyBtn) {
    const canApply = Boolean(state?.deployApproved) && !state?.deployApplied;
    applyBtn.disabled = !canApply;
    applyBtn.title = canApply
      ? "Run terraform apply after approval"
      : "Requires deploy approval and configured credentials";
  }
}

export async function refreshDeployCockpit(runId, { scope = "progress" } = {}) {
  if (!runId || !cockpitRoot(scope)) return;
  try {
    const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=150`);
    renderDeployCockpit(deployStateFromTimeline(timeline.events || []), { scope });
  } catch {
    renderDeployCockpit({ ciStatus: "unavailable", ciDetail: "Timeline unavailable" }, { scope });
  }
}

export async function wireDeployCockpit(runId, { scope = "progress", workspacePath = "" } = {}) {
  const root = cockpitRoot(scope);
  if (!root) return;
  let ws = workspacePath;
  if (!ws && runId) {
    try {
      const timeline = await apiJson(`/runs/${encodeURIComponent(runId)}/timeline?limit=20`);
      for (const ev of timeline.events || []) {
        const project = ev.metadata?.project;
        if (project?.workspace_path) {
          ws = String(project.workspace_path);
          break;
        }
      }
    } catch {
      /* optional */
    }
  }
  const refresh = () => refreshDeployCockpit(runId, { scope });
  root.querySelector(".deploy-cockpit-refresh")?.addEventListener("click", refresh);
  root.querySelector(".deploy-validate-btn")?.addEventListener("click", async () => {
    if (!ws) {
      toast("Workspace path unavailable for this run", "info");
      return;
    }
    try {
      const body = { workspace_path: ws };
      if (runId) body.run_id = runId;
      const result = await apiJson("/platform/deploy/terraform-validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast(`Terraform: ${result.status} — ${result.detail || ""}`, result.status === "passed" ? "success" : "info");
      await refresh();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  root.querySelector(".deploy-approve-btn")?.addEventListener("click", async () => {
    if (!runId) {
      toast("No active run for deploy approval", "info");
      return;
    }
    try {
      await apiJson("/platform/deploy/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId }),
      });
      toast("Deploy approval recorded on run timeline", "success");
      await refresh();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  root.querySelector(".deploy-apply-btn")?.addEventListener("click", async () => {
    if (!runId) {
      toast("No active run for deploy apply", "info");
      return;
    }
    if (!ws) {
      toast("Workspace path unavailable for this run", "info");
      return;
    }
    try {
      const result = await apiJson("/platform/deploy/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, workspace_path: ws }),
      });
      toast(`Deploy apply: ${result.status} — ${result.detail || ""}`, result.status === "passed" ? "success" : "info");
      await refresh();
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  void refresh();
}
