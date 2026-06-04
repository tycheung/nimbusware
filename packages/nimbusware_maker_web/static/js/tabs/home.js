import { apiJson, toast } from "../api-client.js";

export async function mountHome(root) {
  root.innerHTML = `<div id="readiness-mount"></div>
    <h3>Projects</h3>
    <ul id="project-list"></ul>
    <form id="project-form">
      <label>Name <input name="name" required /></label>
      <label>Workspace path <input name="workspace_path" required /></label>
      <button type="submit" class="primary">Create project</button>
    </form>`;

  try {
    const readiness = await apiJson("/platform/readiness");
    const mount = root.querySelector("#readiness-mount");
    if (mount) {
      mount.innerHTML = `<p><strong>Readiness:</strong> ${readiness.status || "unknown"}</p>`;
    }
  } catch (e) {
    toast(String(e.message || e), "error");
  }

  async function refresh() {
    const listing = await apiJson("/projects");
    const list = root.querySelector("#project-list");
    if (!list) return;
    list.replaceChildren();
    for (const p of listing.projects || []) {
      const li = document.createElement("li");
      li.textContent = `${p.name || p.project_id} — ${p.workspace_path || ""}`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Select";
      btn.onclick = () => {
        sessionStorage.setItem("maker_active_project_id", String(p.project_id));
        toast(`Project ${p.name} selected`);
      };
      li.appendChild(btn);
      list.appendChild(li);
    }
  }

  root.querySelector("#project-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    await apiJson("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: fd.get("name"),
        workspace_path: fd.get("workspace_path"),
      }),
    });
    toast("Project created", "success");
    await refresh();
  });

  await refresh();
}
