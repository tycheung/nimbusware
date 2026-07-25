import { useEffect, useState } from "preact/hooks";
import {
  apiJson,
  formatPeelMissMessage,
  formatReadCatchMessage,
  formatWriteCatchMessage,
  isDomainPeelMiss,
  writeMissMessage,
} from "../api/client"; // sak499-d

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
    try {
      const body = await apiJson<{ projects: Project[]; via?: string; error?: string; status?: string }>(
        "/projects",
      );
      if (isDomainPeelMiss(body)) {
        setProjects([]);
        setMsg(formatPeelMissMessage(body, "projects list unavailable"));
        return;
      }
      setProjects(body.projects || []);
      setMsg("");
    } catch (e) {
      setProjects([]);
      setMsg(formatReadCatchMessage(e, "projects list unavailable"));
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function remove(projectId: string) {
    const fallback = "project delete unavailable";
    if (!confirm(`Delete project ${projectId}?`)) return;
    try {
      const body = await apiJson<{ ok?: boolean; via?: string; error?: string; feature?: string }>(
        `/projects/${projectId}`,
        { method: "DELETE" },
      );
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setMsg(miss);
        return;
      }
      setMsg("Deleted");
      await reload();
    } catch (e) {
      setMsg(formatWriteCatchMessage(e, fallback));
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
