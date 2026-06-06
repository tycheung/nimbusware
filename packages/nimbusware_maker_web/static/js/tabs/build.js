import { apiJson, toast } from "../api-client.js";

export async function mountBuild(root) {
  root.innerHTML = `
    <form id="intent-form">
      <label>Project <select name="project_id" id="build-project-select"></select></label>
      <label>Business prompt <textarea name="prompt" rows="5" required></textarea></label>
      <button type="submit" class="primary">Start run</button>
    </form>`;

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
    toast(quickMode ? "Run started" : "Campaign started", "success");
    window.location.hash = `/review?run_id=${runId}`;
    const input = document.getElementById("run-theater-run-id");
    if (input) input.value = runId;
  });
}
