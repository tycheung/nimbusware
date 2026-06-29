import { apiJson } from "../api-client.js";

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
      );
      const events = body.events || [];
      const list = host.querySelector("[data-testid='maker-review-deploy-audit-list']");
      if (!list) return;
      list.replaceChildren();
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
    } catch {
      host.hidden = true;
    }
  }

  root.querySelector("#rev-load-deploy-audit")?.addEventListener("click", () => {
    void load();
  });
  void load();
}
