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
    const body = await apiJson("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: fd.get("project_id"),
        business_prompt: fd.get("prompt"),
        workflow_profile: window.__NIMBUSWARE__?.quick_mode ? "quick_local" : undefined,
      }),
    });
    const runId = body.run_id || body.id;
    toast("Run started", "success");
    window.location.hash = `/review?run_id=${runId}`;
    const input = document.getElementById("run-theater-run-id");
    if (input) input.value = runId;
  });
}
