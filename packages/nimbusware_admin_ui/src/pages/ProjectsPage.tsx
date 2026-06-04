import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type Project = {
  project_id: string;
  name: string;
  workspace_path: string;
  template: string;
};

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [msg, setMsg] = useState("");

  async function reload() {
    const body = await apiJson<{ projects: Project[] }>("/projects");
    setProjects(body.projects || []);
  }

  useEffect(() => {
    reload().catch((e) => setMsg(String((e as Error).message || e)));
  }, []);

  async function remove(projectId: string) {
    if (!confirm(`Delete project ${projectId}?`)) return;
    try {
      await apiJson(`/projects/${projectId}`, { method: "DELETE" });
      setMsg("Deleted");
      await reload();
    } catch (e) {
      setMsg(String((e as Error).message || e));
    }
  }

  return (
    <section>
      <h2>Projects</h2>
      <p class="muted">Delete requires admin token from sign-in.</p>
      {msg ? <p class="hint">{msg}</p> : null}
      {!projects.length ? <p>No projects.</p> : null}
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Workspace</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr key={p.project_id}>
              <td>{p.name}</td>
              <td>
                <code>{p.workspace_path}</code>
              </td>
              <td>
                <button type="button" onClick={() => remove(p.project_id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
