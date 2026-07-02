import { apiJson, toast } from "../api-client.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";
import { formatGateSummary } from "../gate-summary.js";
import { renderPendingCards } from "./review_cards_ui.js";
import { wireReviewGitPanel, mountReviewDeployAuditPanel } from "./review_git_ui.js";
import { wireReviewAdvancedPanel } from "./review_advanced_ui.js";
import { deployCockpitHtml, wireDeployCockpit } from "../deploy_cockpit.js";

export async function mountReview(root) {
  root.innerHTML = `
    <div class="actions">
      <button type="button" id="rev-load-pending" data-testid="maker-review-refresh">Refresh approval</button>
      <button type="button" id="rev-load-research">Research briefs</button>
    </div>
    <div id="rev-summary" class="approval-cards"></div>
    <div id="rev-actions" class="actions"></div>
    <ul id="rev-research"></ul>
    <details class="review-advanced-panel mobile-advanced" data-testid="maker-review-advanced">
      <summary>Advanced: diff, stitch, revert</summary>
      <div class="actions">
        <button type="button" id="rev-load-diff" data-testid="maker-review-load-diff">Slice diff</button>
        <button type="button" id="rev-revert" data-testid="maker-review-revert">Revert workspace</button>
        <button type="button" id="rev-load-stitch" data-testid="maker-review-load-stitch">Load stitch summary</button>
      </div>
      <section id="rev-stitch" class="stitch-panel">
        <pre id="rev-stitch-body" class="json-pre"></pre>
      </section>
      <pre id="rev-diff" class="diff-pre"></pre>
    </details>
    <section id="rev-launch-eval" class="launch-panel hidden mobile-advanced">
      <h3>Launch readiness</h3>
      <button type="button" id="rev-load-launch-eval" data-testid="maker-review-launch-scorecard">Load scorecard</button>
      <button type="button" id="rev-run-launch-eval" data-testid="maker-review-run-launch-eval">Run launch check</button>
      <div id="rev-launch-eval-body" class="launch-scorecard" data-testid="maker-review-scorecard-body"></div>
    </section>
    ${deployCockpitHtml({ scope: "review" })}
    <section id="rev-deploy-audit" class="panel" data-testid="maker-review-deploy-audit" hidden>
      <h3>Deploy audit</h3>
      <p class="muted">Credential updates and apply/rollback actions for this run (hashed user refs only).</p>
      <button type="button" id="rev-load-deploy-audit" data-testid="maker-review-deploy-audit-refresh">
        Refresh audit timeline
      </button>
      <div data-testid="maker-review-deploy-audit-list"></div>
    </section>
    <section id="rev-git-panel" class="panel mobile-advanced" data-testid="maker-review-git-panel">
      <h3>Git &amp; pull request</h3>
      <p id="rev-git-status" class="muted"></p>
      <div id="rev-git-actions" class="actions"></div>
      <p class="muted">
        <a id="rev-audit-export" href="#" download hidden data-testid="maker-review-audit-export">
          Download compliance bundle
        </a>
        <a id="rev-fleet-audit-export" href="/v1/enterprise/audit-export" download hidden data-testid="maker-review-fleet-audit-export">
          Download fleet audit export
        </a>
      </p>
    </section>
    <section id="rev-factory-evidence" class="panel mobile-advanced" data-testid="maker-review-factory-evidence">
      <h3>Factory evidence</h3>
      <button type="button" id="rev-load-factory-evidence" data-testid="maker-review-factory-evidence-load">
        Load scorecard
      </button>
      <table class="data-table" id="rev-factory-evidence-table" hidden>
        <thead><tr><th>Dimension</th><th>Value</th></tr></thead>
        <tbody id="rev-factory-evidence-rows"></tbody>
      </table>
      <p id="rev-factory-evidence-empty" class="muted" hidden>No factory evidence on this run yet.</p>
      <p id="rev-factory-evidence-links" class="muted" hidden>
        <a id="rev-factory-evidence-html" href="#" target="_blank" rel="noopener" data-testid="maker-review-factory-evidence-html">
          Open HTML scorecard
        </a>
        ·
        <a id="rev-factory-evidence-zip" href="#" download data-testid="maker-review-factory-evidence-zip">
          Download zip
        </a>
      </p>
    </section>`;

  async function currentRunId() {
    let id = resolveRunId();
    if (!id) id = await hydrateActiveRun(apiJson);
    return id;
  }

  const git = wireReviewGitPanel(root, { currentRunId });
  wireReviewAdvancedPanel(root, { currentRunId });
  mountReviewDeployAuditPanel(root, { currentRunId });

  async function loadPending() {
    const id = await currentRunId();
    if (!id) return toast("Enter a run ID", "error");
    const body = await apiJson(`/runs/${id}/maker/pending`);
    renderPendingCards(body, root.querySelector("#rev-summary"));
    try {
      const progress = await apiJson(`/runs/${encodeURIComponent(id)}/maker-progress?simple=true`);
      const gateText = formatGateSummary(progress.gate_summary);
      if (gateText) {
        const statusCard = root.querySelector('[data-testid="maker-review-status-card"]');
        if (statusCard && !statusCard.querySelector('[data-testid="maker-review-gate-summary"]')) {
          const gateLine = document.createElement("p");
          gateLine.className = "gate-summary-banner";
          gateLine.dataset.testid = "maker-review-gate-summary";
          gateLine.textContent = gateText;
          statusCard.appendChild(gateLine);
          const link = document.createElement("a");
          link.href = `#/progress?run_id=${encodeURIComponent(id)}`;
          link.className = "linkish";
          link.textContent = "Recover on Progress";
          link.dataset.testid = "maker-review-gate-recover-link";
          statusCard.appendChild(link);
        }
      }
    } catch {
      /* optional */
    }
    const actions = root.querySelector("#rev-actions");
    actions.replaceChildren();
    if (!body.plan_approved) {
      const b = document.createElement("button");
      b.textContent = "Approve plan";
      b.dataset.testid = "maker-review-approve-plan";
      b.onclick = () => apiJson(`/runs/${id}/maker/plan/approve`, { method: "POST" }).then(loadPending);
      actions.appendChild(b);
    }
    if (body.awaiting_approval && body.pending) {
      const sid = body.pending.slice_id || body.pending.id;
      for (const [label, path, payload] of [
        ["Apply", "apply", { slice_id: String(sid) }],
        ["Skip", "skip", { slice_id: String(sid) }],
      ]) {
        const b = document.createElement("button");
        b.textContent = label;
        b.dataset.testid = path === "apply" ? "maker-review-apply-slice" : `maker-review-${path}-slice`;
        b.onclick = () =>
          apiJson(`/runs/${id}/maker/slices/${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          }).then(loadPending);
        actions.appendChild(b);
      }
    }
  }

  root.querySelector("#rev-load-pending")?.addEventListener("click", () => {
    loadPending().then(git.loadGitStatus).catch((e) => toast(String(e.message), "error"));
  });
  void git.loadGitStatus();
  const initialId = await currentRunId();
  if (initialId) {
    wireDeployCockpit(initialId, { scope: "review" });
    loadPending().catch(() => {});
  }
}
