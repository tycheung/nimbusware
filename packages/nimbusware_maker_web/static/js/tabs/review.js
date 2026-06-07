import { apiJson, toast } from "../api-client.js";

function runId() {
  const search = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.split("?")[1] || "");
  const fromField =
    document.getElementById("run-theater-run-id")?.value?.trim() ||
    document.getElementById("desktop-run-id")?.value?.trim() ||
    document.getElementById("mobile-run-id")?.value?.trim() ||
    "";
  return search.get("run_id") || hashParams.get("run_id") || fromField;
}

export async function mountReview(root) {
  root.innerHTML = `
    <div class="actions">
      <button type="button" id="rev-load-pending" data-testid="maker-review-refresh">Refresh approval</button>
      <button type="button" id="rev-load-research">Research briefs</button>
      <button type="button" id="rev-load-diff" class="mobile-advanced">Slice diff</button>
      <button type="button" id="rev-revert" class="mobile-advanced">Revert workspace</button>
    </div>
    <p id="rev-summary"></p>
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
      <div id="rev-launch-eval-body" class="launch-scorecard" data-testid="maker-review-scorecard-body"></div>
    </section>
    <p id="rev-git-status" class="muted"></p>`;

  async function loadGitStatus() {
    const id = runId();
    if (!id) return;
    const el = root.querySelector("#rev-git-status");
    try {
      const body = await apiJson(`/runs/${id}/maker/git-status`);
      const gc = body.git_commit;
      if (!gc) {
        el.textContent = "Git: no per-slice commits recorded yet.";
        return;
      }
      const status = gc.status || "unknown";
      const branch = gc.branch ? ` on ${gc.branch}` : "";
      const sha = gc.sha ? ` (${String(gc.sha).slice(0, 8)})` : "";
      const reason = gc.reason ? ` — ${gc.reason}` : "";
      el.textContent = `Git ${status}${branch}${sha}${reason}`;
    } catch {
      el.textContent = "";
    }
  }

  async function loadPending() {
    const id = runId();
    if (!id) return toast("Enter a run ID", "error");
    const body = await apiJson(`/runs/${id}/maker/pending`);
    root.querySelector("#rev-summary").textContent = JSON.stringify(body, null, 2);
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
  root.querySelector("#rev-load-research")?.addEventListener("click", async () => {
    const id = runId();
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
    const id = runId();
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
    const id = runId();
    const pending = await apiJson(`/runs/${id}/maker/pending`);
    const idx = pending?.pending?.slice_index ?? 0;
    const diff = await apiJson(`/runs/${id}/slices/${idx}/diff`);
    root.querySelector("#rev-diff").textContent = diff.patch || diff.diff || JSON.stringify(diff, null, 2);
  });
  root.querySelector("#rev-revert")?.addEventListener("click", async () => {
    const id = runId();
    await apiJson(`/runs/${id}/workspace/revert`, { method: "POST" });
    toast("Workspace reverted", "success");
  });

  function renderLaunchScorecard(container, scorecard) {
    container.replaceChildren();
    const dims = [
      ["aggregate", scorecard.aggregate],
      ["maturity", scorecard.maturity],
      ["maintainability", scorecard.maintainability],
      ["scalability", scorecard.scalability],
      ["security", scorecard.security],
      ["testability", scorecard.testability],
    ];
    const table = document.createElement("table");
    table.className = "scorecard-table";
    const tbody = document.createElement("tbody");
    for (const [label, value] of dims) {
      if (value == null) continue;
      const tr = document.createElement("tr");
      tr.innerHTML = `<th scope="row">${label}</th><td>${value}</td>`;
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    container.appendChild(table);
    if (scorecard.passed != null) {
      const status = document.createElement("p");
      status.textContent = scorecard.passed ? "passed" : "needs work";
      status.dataset.testid = "maker-review-scorecard-status";
      container.appendChild(status);
    }
    const llmDims = scorecard.llm_dimensions;
    if (llmDims && typeof llmDims === "object" && Object.keys(llmDims).length) {
      const heading = document.createElement("h4");
      heading.textContent = "LLM dimensions";
      container.appendChild(heading);
      const llmTable = document.createElement("table");
      llmTable.dataset.testid = "maker-review-llm-dimensions";
      const llmBody = document.createElement("tbody");
      for (const [key, val] of Object.entries(llmDims)) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<th scope="row">${key}</th><td>${val}</td>`;
        llmBody.appendChild(tr);
      }
      llmTable.appendChild(llmBody);
      container.appendChild(llmTable);
    }
    const findings = scorecard.findings || scorecard.llm_findings;
    if (Array.isArray(findings) && findings.length) {
      const ul = document.createElement("ul");
      for (const item of findings.slice(0, 8)) {
        const li = document.createElement("li");
        li.textContent = String(item);
        ul.appendChild(li);
      }
      container.appendChild(ul);
    }
  }

  root.querySelector("#rev-load-launch-eval")?.addEventListener("click", async () => {
    const id = runId();
    if (!id) return toast("Enter a run ID", "error");
    const timeline = await apiJson(`/runs/${id}/timeline`);
    const events = timeline.events || [];
    let scorecard = null;
    for (let i = events.length - 1; i >= 0; i -= 1) {
      const ev = events[i];
      if (ev.event_type !== "stage.passed") continue;
      const payload = ev.payload || {};
      if (payload.stage_name !== "launch_eval.completed") continue;
      scorecard = ev.metadata || payload;
      break;
    }
    const panel = root.querySelector("#rev-launch-eval");
    panel?.classList.remove("hidden");
    const body = root.querySelector("#rev-launch-eval-body");
    if (!scorecard) {
      body.replaceChildren();
      body.textContent = "No launch_eval.completed event on this run yet.";
      return;
    }
    renderLaunchScorecard(body, scorecard);
  });
}
