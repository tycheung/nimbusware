import { apiJson, toast } from "../api-client.js";
import { formatDomainMissMessage, isDomainPeelMiss, toastIfMiss } from "../broker_miss.js"; // sak499-b
import { deployStateFromTimeline } from "../deploy_cockpit.js";
import { mountReviewCommitPolicyPanel } from "./review_commit_ui.js";

function formatAuditRow(row) {
  const when = String(row.occurred_at || "").replace("T", " ").slice(0, 19);
  const event = String(row.event || "event");
  const target = row.deploy_target ? ` · ${row.deploy_target}` : "";
  const detail = row.detail ? ` — ${row.detail}` : "";
  const userRef = row.user_ref ? `user ${row.user_ref}` : "";
  const parts = [when, event, userRef, target, detail].filter(Boolean);
  return parts.join(" ");
}

export function mountReviewDeployAuditPanel(root, { currentRunId }) {
  const host = root.querySelector("#rev-deploy-audit");
  if (!host) return;

  async function load() {
    const id = await currentRunId();
    if (!id) {
      host.hidden = true;
      return;
    }
    try {
      const body = await apiJson(
        `/platform/deploy/audit?run_id=${encodeURIComponent(id)}&limit=40`,
      ).catch((e) => ({
        via: "broker_miss",
        error: String(e.message || e),
        feature: "deploy_audit",
        events: [],
      }));
      const list = host.querySelector("[data-testid='maker-review-deploy-audit-list']");
      if (!list) return;
      list.replaceChildren();
      if (isDomainPeelMiss(body)) {
        toastIfMiss(body, toast, "Deploy audit unavailable");
        const miss = document.createElement("p");
        miss.className = "muted";
        miss.dataset.testid = "maker-review-deploy-audit-miss";
        miss.textContent =
          formatDomainMissMessage(body, "Deploy audit unavailable") || "Deploy audit unavailable";
        list.appendChild(miss);
        host.hidden = false;
        return;
      }
      const events = body.events || [];
      if (!events.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.dataset.testid = "maker-review-deploy-audit-empty";
        empty.textContent = "No deploy audit events for this run yet.";
        list.appendChild(empty);
        host.hidden = false;
        return;
      }
      const ul = document.createElement("ul");
      ul.className = "deploy-audit-timeline";
      ul.dataset.testid = "maker-review-deploy-audit-rows";
      for (const row of events) {
        const li = document.createElement("li");
        li.dataset.testid = "maker-review-deploy-audit-row";
        li.textContent = formatAuditRow(row);
        ul.appendChild(li);
      }
      list.appendChild(ul);
      host.hidden = false;
    } catch (e) {
      host.hidden = false;
      const list = host.querySelector("[data-testid='maker-review-deploy-audit-list']");
      list?.replaceChildren();
      const miss = document.createElement("p");
      miss.className = "muted";
      miss.textContent = String(e.message || e);
      list?.appendChild(miss);
      toast(String(e.message || e), "error");
    }
  }

  root.querySelector("#rev-load-deploy-audit")?.addEventListener("click", () => {
    void load();
  });
  void load();
}

export function wireReviewGitPanel(root, { currentRunId }) {
  let commitPolicyMounted = false;

  async function ensureCommitPolicyPanel() {
    if (commitPolicyMounted) return;
    try {
      const readiness = await apiJson("/platform/readiness");
      if (isDomainPeelMiss(readiness)) return;
      if (readiness.setup_bundle !== "enterprise") return;
      const policy = await apiJson("/enterprise/tenants/default/commit-policy").catch((e) => ({
        via: "broker_miss",
        error: String(e.message || e),
        feature: "fleet_commit_policy",
      }));
      if (toastIfMiss(policy, toast, "Commit policy unavailable")) {
        return;
      }
      mountReviewCommitPolicyPanel(root, {
        setupBundle: readiness.setup_bundle,
        messageRegex: policy.message_regex || "",
      });
      commitPolicyMounted = true;
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  }
  async function loadGitStatus() {
    await ensureCommitPolicyPanel();
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
        fleetAudit.hidden =
          isDomainPeelMiss(readiness) || readiness.setup_bundle !== "enterprise";
      }
    } catch {
      if (fleetAudit) fleetAudit.hidden = true;
    }
    const el = root.querySelector("#rev-git-status");
    const actions = root.querySelector("#rev-git-actions");
    if (actions) actions.replaceChildren();
    try {
      const [body, timeline] = await Promise.all([
        apiJson(`/runs/${id}/maker/git-status`).catch((e) => ({
          via: "broker_miss",
          error: String(e.message || e),
          feature: "git_status",
        })),
        apiJson(`/runs/${id}/timeline?limit=120`).catch((e) => ({
          via: "broker_miss",
          error: String(e.message || e),
          feature: "run_timeline",
          events: [],
        })),
      ]);
      if (isDomainPeelMiss(body)) {
        toastIfMiss(body, toast, "Git status unavailable");
        el.textContent =
          formatDomainMissMessage(body, "Git status unavailable") || "Git status unavailable";
        return;
      }
      if (isDomainPeelMiss(timeline)) {
        toastIfMiss(timeline, toast, "Run timeline unavailable");
      }
      const deploy = deployStateFromTimeline(
        isDomainPeelMiss(timeline) ? [] : timeline.events || [],
      );
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
            if (toastIfMiss(res, toast, "Open pull request unavailable")) return;
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
    } catch (e) {
      el.textContent = String(e.message || e);
      toast(String(e.message || e), "error");
    }
  }

  return { loadGitStatus };
}
