import { apiJson, toast } from "../api-client.js";
import { setActiveProjectId, setActiveRun, syncRunIdToShell } from "../session-hub.js";

function campaignModeFromHash() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
  return params.get("campaign") === "1";
}

export async function mountBuild(root) {
  const campaignMode = campaignModeFromHash() && !window.__NIMBUSWARE__?.quick_mode;
  root.innerHTML = `
    <p id="build-mode-banner" class="build-mode-banner" data-testid="maker-build-mode-banner"></p>
    <form id="intent-form">
      <label>Project <select name="project_id" id="build-project-select"></select></label>
      <label>Business prompt <textarea name="prompt" rows="5" required></textarea></label>
      <button type="submit" class="primary" data-testid="maker-build-start-run">${campaignMode ? "Start campaign" : "Start run"}</button>
    </form>`;

  const banner = root.querySelector("#build-mode-banner");
  if (banner) {
    if (campaignMode) {
      banner.textContent = "Campaign mode — autonomous delivery backlog and slice execution.";
      banner.dataset.mode = "campaign";
    } else if (window.__NIMBUSWARE__?.quick_mode) {
      banner.textContent = "Quick local mode — in-memory runs.";
      banner.dataset.mode = "quick";
    } else {
      banner.hidden = true;
    }
  }

  const listing = await apiJson("/projects");
  const sel = root.querySelector("#build-project-select");
  for (const p of listing.projects || []) {
    const opt = document.createElement("option");
    opt.value = p.project_id;
    opt.textContent = p.name || p.project_id;
    sel?.appendChild(opt);
  }
  const saved = sessionStorage.getItem("maker_active_project_id");
  if (saved && sel) sel.value = saved;

  root.querySelector("#intent-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const quickMode = window.__NIMBUSWARE__?.quick_mode;
    const endpoint = quickMode ? "/runs" : "/campaigns";
    const payload = quickMode
      ? {
          project_id: fd.get("project_id"),
          requirements: { business_prompt: fd.get("prompt") },
          workflow_profile: "quick_local",
        }
      : {
          project_id: fd.get("project_id"),
          requirements: { business_prompt: fd.get("prompt") },
          autonomous: true,
          workflow_profile: "campaign_micro_slice",
        };
    const body = await apiJson(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const runId = body.run_id || body.campaign_id || body.id;
    const projectId = String(fd.get("project_id") || "");
    if (projectId) {
      setActiveProjectId(projectId);
      setActiveRun(projectId, runId);
    }
    syncRunIdToShell(runId);
    toast(quickMode ? "Run started" : "Campaign started", "success");
    window.location.hash = `/progress?run_id=${encodeURIComponent(runId)}`;
  });
}
