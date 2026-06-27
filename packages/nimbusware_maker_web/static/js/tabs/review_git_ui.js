import { apiJson, toast } from "../api-client.js";
import { deployStateFromTimeline } from "../deploy_cockpit.js";

export function wireReviewGitPanel(root, { currentRunId }) {
  async function loadGitStatus() {
    const id = await currentRunId();
    if (!id) return;
    const auditLink = root.querySelector("#rev-audit-export");
    const fleetAudit = root.querySelector("#rev-fleet-audit-export");
    if (auditLink) {
      auditLink.href = `/v1/runs/${encodeURIComponent(id)}/audit-export`;
      auditLink.hidden = false;
    }
    try {
      const readiness = await apiJson("/platform/readiness");
      if (fleetAudit) {
        fleetAudit.hidden = readiness.setup_bundle !== "enterprise";
      }
    } catch {
      if (fleetAudit) fleetAudit.hidden = true;
    }
    const el = root.querySelector("#rev-git-status");
    const actions = root.querySelector("#rev-git-actions");
    if (actions) actions.replaceChildren();
    try {
      const [body, timeline] = await Promise.all([
        apiJson(`/runs/${id}/maker/git-status`),
        apiJson(`/runs/${id}/timeline?limit=120`).catch(() => ({ events: [] })),
      ]);
      const deploy = deployStateFromTimeline(timeline.events || []);
      const gc = body.git_commit;
      const outputs = body.git_outputs || {};
      const branch = outputs.branch || gc?.branch || "";
      const prUrl = outputs.pr_url || "";
      const prStatus = outputs.pr_status || "";
      const lines = [];
      if (deploy.ciStatus && deploy.ciStatus !== "not_started") {
        lines.push(
          `CI: ${deploy.ciStatus}${deploy.ciDetail ? ` — ${deploy.ciDetail}` : ""}`,
        );
      }
      if (gc) {
        const status = gc.status || "unknown";
        const sha = gc.sha ? ` (${String(gc.sha).slice(0, 8)})` : "";
        const reason = gc.reason ? ` — ${gc.reason}` : "";
        lines.push(`Last commit: ${status}${sha}${reason}`);
      } else {
        lines.push("No per-slice commits recorded yet.");
      }
      if (branch) lines.push(`Branch: ${branch}`);
      if (prUrl) lines.push(`PR: ${prUrl}`);
      if (prStatus) lines.push(`PR status: ${prStatus}`);
      el.textContent = lines.join(" · ");
      el.dataset.testid = "maker-review-git-status";
      if (branch && actions) {
        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.textContent = "Copy branch name";
        copyBtn.dataset.testid = "maker-review-copy-branch";
        copyBtn.onclick = () => {
          navigator.clipboard?.writeText(branch);
          toast("Branch copied", "success");
        };
        actions.appendChild(copyBtn);
      }
      if (!prUrl && branch && actions) {
        const prBtn = document.createElement("button");
        prBtn.type = "button";
        prBtn.className = "primary";
        prBtn.textContent = "Open pull request";
        prBtn.dataset.testid = "maker-review-open-pr";
        prBtn.onclick = async () => {
          try {
            const res = await apiJson(`/runs/${id}/maker/open-pr`, { method: "POST" });
            const url = res?.pr?.pr_url;
            if (url) window.open(url, "_blank", "noopener");
            toast(url ? "Pull request opened" : "PR step completed", "success");
            await loadGitStatus();
          } catch (e) {
            toast(String(e.message || e), "error");
          }
        };
        actions.appendChild(prBtn);
      }
      if (prUrl && actions) {
        const open = document.createElement("a");
        open.href = prUrl;
        open.target = "_blank";
        open.rel = "noopener";
        open.textContent = "View pull request";
        open.dataset.testid = "maker-review-view-pr";
        open.className = "primary";
        actions.appendChild(open);
      }
    } catch {
      el.textContent = "";
    }
  }

  return { loadGitStatus };
}
