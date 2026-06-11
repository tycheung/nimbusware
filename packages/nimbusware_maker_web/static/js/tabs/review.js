import { apiJson, toast } from "../api-client.js";
import { renderLaunchScorecard, scorecardFromTimeline } from "../launch-scorecard.js";
import { hydrateActiveRun, resolveRunId } from "../session-hub.js";

function renderPendingCards(body, container) {
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

export async function mountReview(root) {
  root.innerHTML = `
    <div class="actions">
      <button type="button" id="rev-load-pending" data-testid="maker-review-refresh">Refresh approval</button>
      <button type="button" id="rev-load-research">Research briefs</button>
      <button type="button" id="rev-load-diff" class="mobile-advanced">Slice diff</button>
      <button type="button" id="rev-revert" class="mobile-advanced">Revert workspace</button>
    </div>
    <div id="rev-summary" class="approval-cards"></div>
    <div id="rev-actions" class="actions"></div>
    <ul id="rev-research"></ul>
    <section id="rev-stitch" class="stitch-panel hidden mobile-advanced">
      <h3>Stitch / transplant</h3>
      <button type="button" id="rev-load-stitch" class="mobile-advanced">Load stitch summary</button>
      <pre id="rev-stitch-body" class="json-pre"></pre>
    </section>
    <pre id="rev-diff" class="diff-pre"></pre>
    <section id="rev-launch-eval" class="launch-panel hidden">
      <h3>Launch readiness</h3>
      <button type="button" id="rev-load-launch-eval" data-testid="maker-review-launch-scorecard">Load scorecard</button>
      <button type="button" id="rev-run-launch-eval" data-testid="maker-review-run-launch-eval">Run launch check</button>
      <div id="rev-launch-eval-body" class="launch-scorecard" data-testid="maker-review-scorecard-body"></div>
    </section>
    <section id="rev-git-panel" class="panel" data-testid="maker-review-git-panel">
      <h3>Git &amp; pull request</h3>
      <p id="rev-git-status" class="muted"></p>
      <div id="rev-git-actions" class="actions"></div>
    </section>
    <section id="rev-factory-evidence" class="panel" data-testid="maker-review-factory-evidence">
      <h3>Factory evidence</h3>
      <button type="button" id="rev-load-factory-evidence" data-testid="maker-review-factory-evidence-load">
        Load scorecard
      </button>
      <table class="data-table" id="rev-factory-evidence-table" hidden>
        <thead><tr><th>Dimension</th><th>Value</th></tr></thead>
        <tbody id="rev-factory-evidence-rows"></tbody>
      </table>
      <p id="rev-factory-evidence-empty" class="muted" hidden>No factory evidence on this run yet.</p>
    </section>`;

  async function currentRunId() {
    let id = resolveRunId();
    if (!id) id = await hydrateActiveRun(apiJson);
    return id;
  }

  async function loadGitStatus() {
    const id = await currentRunId();
    if (!id) return;
    const el = root.querySelector("#rev-git-status");
    const actions = root.querySelector("#rev-git-actions");
    if (actions) actions.replaceChildren();
    try {
      const body = await apiJson(`/runs/${id}/maker/git-status`);
      const gc = body.git_commit;
      const outputs = body.git_outputs || {};
      const branch = outputs.branch || gc?.branch || "";
      const prUrl = outputs.pr_url || "";
      const lines = [];
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
      el.textContent = lines.join(" · ");
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

  async function loadPending() {
    const id = await currentRunId();
    if (!id) return toast("Enter a run ID", "error");
    const body = await apiJson(`/runs/${id}/maker/pending`);
    renderPendingCards(body, root.querySelector("#rev-summary"));
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
    loadPending().then(loadGitStatus).catch((e) => toast(String(e.message), "error"));
  });
  void loadGitStatus();
  const initialId = await currentRunId();
  if (initialId) {
    loadPending().catch(() => {});
  }

  root.querySelector("#rev-load-research")?.addEventListener("click", async () => {
    const id = await currentRunId();
    const body = await apiJson(`/runs/${id}/research`);
    const ul = root.querySelector("#rev-research");
    ul.replaceChildren();
    for (const brief of body.briefs || []) {
      const li = document.createElement("li");
      const bid = brief.brief_id || brief.artifact_id;
      li.textContent = `${bid} — ${brief.review_status || brief.status}`;
      if ((brief.review_status || brief.status) === "pending") {
        const approve = document.createElement("button");
        approve.textContent = "Approve";
        approve.onclick = () =>
          apiJson(`/runs/${id}/research/${encodeURIComponent(bid)}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: "" }),
          });
        const reject = document.createElement("button");
        reject.textContent = "Reject";
        reject.onclick = () =>
          apiJson(`/runs/${id}/research/${encodeURIComponent(bid)}/reject`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: "" }),
          });
        li.append(approve, reject);
      }
      ul.appendChild(li);
    }
  });
  root.querySelector("#rev-load-stitch")?.addEventListener("click", async () => {
    const id = await currentRunId();
    if (!id) return toast("Enter a run ID", "error");
    const body = await apiJson(`/runs/${id}/stitch-summary`);
    const panel = root.querySelector("#rev-stitch");
    panel?.classList.remove("hidden");
    const lines = (body.events || []).map(
      (ev) => `#${ev.store_seq} ${ev.event_type}: ${ev.summary || ""}`,
    );
    const outcome = body.transplant_outcome
      ? `\nTransplant outcome: ${body.transplant_outcome}`
      : "";
    root.querySelector("#rev-stitch-body").textContent =
      (lines.length ? lines.join("\n") : "No stitch events for this run.") + outcome;
  });
  root.querySelector("#rev-load-diff")?.addEventListener("click", async () => {
    const id = await currentRunId();
    const pending = await apiJson(`/runs/${id}/maker/pending`);
    const idx = pending?.pending?.slice_index ?? 0;
    const diff = await apiJson(`/runs/${id}/slices/${idx}/diff`);
    root.querySelector("#rev-diff").textContent = diff.patch || diff.diff || JSON.stringify(diff, null, 2);
  });
  root.querySelector("#rev-revert")?.addEventListener("click", async () => {
    const id = await currentRunId();
    await apiJson(`/runs/${id}/workspace/revert`, { method: "POST" });
    toast("Workspace reverted", "success");
  });

  function renderLaunchScorecardLocal(container, scorecard) {
    renderLaunchScorecard(container, scorecard, { testIdPrefix: "maker-review" });
  }

  async function showLaunchScorecard(id) {
    const panel = root.querySelector("#rev-launch-eval");
    panel?.classList.remove("hidden");
    const body = root.querySelector("#rev-launch-eval-body");
    const scorecard = await scorecardFromTimeline(apiJson, id);
    if (!scorecard) {
      body.replaceChildren();
      body.textContent = "No launch_eval.completed event on this run yet.";
      return;
    }
    renderLaunchScorecardLocal(body, scorecard);
  }

  root.querySelector("#rev-load-launch-eval")?.addEventListener("click", async () => {
    const id = await currentRunId();
    if (!id) return toast("Enter a run ID", "error");
    try {
      await showLaunchScorecard(id);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  root.querySelector("#rev-run-launch-eval")?.addEventListener("click", async () => {
    const id = await currentRunId();
    if (!id) return toast("Enter a run ID", "error");
    try {
      await apiJson(`/runs/${id}/maker/launch-eval`, { method: "POST" });
      await showLaunchScorecard(id);
      toast("Launch check complete", "success");
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });

  async function loadFactoryEvidenceScorecard() {
    const id = await currentRunId();
    if (!id) return toast("Enter a run ID", "error");
    const table = root.querySelector("#rev-factory-evidence-table");
    const tbody = root.querySelector("#rev-factory-evidence-rows");
    const empty = root.querySelector("#rev-factory-evidence-empty");
    try {
      const body = await apiJson(`/runs/${id}/factory-evidence`);
      const rows = body.scorecard_rows || [];
      if (!rows.length) {
        table.hidden = true;
        empty.hidden = false;
        empty.textContent = "No factory evidence on this run yet.";
        return;
      }
      empty.hidden = true;
      table.hidden = false;
      tbody.replaceChildren();
      for (const row of rows) {
        const tr = document.createElement("tr");
        tr.dataset.testid = `maker-factory-evidence-row-${String(row.dimension || "")
          .toLowerCase()
          .replace(/\s+/g, "-")}`;
        const dim = document.createElement("td");
        dim.textContent = row.dimension || "";
        const val = document.createElement("td");
        val.textContent = row.value || "";
        tr.append(dim, val);
        tbody.appendChild(tr);
      }
    } catch (e) {
      table.hidden = true;
      empty.hidden = false;
      empty.textContent = String(e.message || e);
    }
  }

  root.querySelector("#rev-load-factory-evidence")?.addEventListener("click", () => {
    void loadFactoryEvidenceScorecard();
  });
}
