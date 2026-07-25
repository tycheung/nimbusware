import { apiJson, toast } from "../api-client.js";
import { formatDomainMissMessage, isDomainPeelMiss, toastIfMiss } from "../broker_miss.js"; // sak499-b
import { renderLaunchScorecard, fetchScorecardForRun } from "../launch-scorecard.js";

export function wireReviewAdvancedPanel(root, { currentRunId }) {
  root.querySelector("#rev-load-research")?.addEventListener("click", async () => {
    const id = await currentRunId();
    const body = await apiJson(`/runs/${id}/research`);
    const ul = root.querySelector("#rev-research");
    ul.replaceChildren();
    if (isDomainPeelMiss(body)) {
      const li = document.createElement("li");
      li.dataset.testid = "maker-review-research-miss";
      li.textContent =
        formatDomainMissMessage(body, "Research briefs unavailable") || "Research briefs unavailable";
      ul.appendChild(li);
      toastIfMiss(body, toast, "Research briefs unavailable");
      return;
    }
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
          }).then((r) => toastIfMiss(r, toast, "Research approve unavailable"));
        const reject = document.createElement("button");
        reject.textContent = "Reject";
        reject.onclick = () =>
          apiJson(`/runs/${id}/research/${encodeURIComponent(bid)}/reject`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: "" }),
          }).then((r) => toastIfMiss(r, toast, "Research reject unavailable"));
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
    if (toastIfMiss(body, toast, "Stitch summary unavailable")) {
      root.querySelector("#rev-stitch-body").textContent =
        formatDomainMissMessage(body, "Stitch summary unavailable") || "Stitch summary unavailable";
      return;
    }
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
    if (toastIfMiss(pending, toast, "Pending slice unavailable")) return;
    const idx = pending?.pending?.slice_index ?? 0;
    const diff = await apiJson(`/runs/${id}/slices/${idx}/diff`);
    if (toastIfMiss(diff, toast, "Slice diff unavailable")) return;
    root.querySelector("#rev-diff").textContent = diff.patch || diff.diff || JSON.stringify(diff, null, 2);
  });

  root.querySelector("#rev-revert")?.addEventListener("click", async () => {
    const id = await currentRunId();
    const result = await apiJson(`/runs/${id}/workspace/revert`, { method: "POST" });
    if (toastIfMiss(result, toast, "Workspace revert unavailable")) return;
    toast("Workspace reverted", "success");
  });

  async function showLaunchScorecard(id) {
    const panel = root.querySelector("#rev-launch-eval");
    panel?.classList.remove("hidden");
    const body = root.querySelector("#rev-launch-eval-body");
    const scorecard = await fetchScorecardForRun(apiJson, id);
    if (!scorecard) {
      body.replaceChildren();
      body.textContent = "No launch_eval.completed event on this run yet.";
      return;
    }
    if (isDomainPeelMiss(scorecard)) {
      body.replaceChildren();
      body.textContent =
        formatDomainMissMessage(scorecard, "Launch eval unavailable") || "Launch eval unavailable";
      toastIfMiss(scorecard, toast, "Launch eval unavailable");
      return;
    }
    renderLaunchScorecard(body, scorecard, { testIdPrefix: "maker-review" });
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
      const result = await apiJson(`/runs/${id}/maker/launch-eval`, { method: "POST" });
      if (toastIfMiss(result, toast, "Launch eval unavailable")) return;
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
    const links = root.querySelector("#rev-factory-evidence-links");
    const htmlLink = root.querySelector("#rev-factory-evidence-html");
    const zipLink = root.querySelector("#rev-factory-evidence-zip");
    try {
      const body = await apiJson(`/runs/${id}/factory-evidence`);
      if (isDomainPeelMiss(body)) {
        table.hidden = true;
        if (links) links.hidden = true;
        empty.hidden = false;
        empty.textContent =
          formatDomainMissMessage(body, "Factory evidence unavailable") || "Factory evidence unavailable";
        toastIfMiss(body, toast, "Factory evidence unavailable");
        return;
      }
      const rows = body.scorecard_rows || [];
      if (!rows.length) {
        table.hidden = true;
        if (links) links.hidden = true;
        empty.hidden = false;
        empty.textContent = "No factory evidence on this run yet.";
        return;
      }
      empty.hidden = true;
      table.hidden = false;
      if (links) links.hidden = false;
      if (htmlLink) htmlLink.href = `/v1/runs/${encodeURIComponent(id)}/factory-evidence/scorecard.html`;
      if (zipLink) zipLink.href = `/v1/runs/${encodeURIComponent(id)}/factory-evidence/export`;
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
