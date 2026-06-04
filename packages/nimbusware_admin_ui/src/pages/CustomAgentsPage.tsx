import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type Agent = { id: string; display_name: string; system_prompt: string; description?: string };

export function CustomAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ agents: Agent[] }>("/custom-agents")
      .then((b) => setAgents(b.agents || []))
      .catch((e) => setError(String((e as Error).message || e)));
  }, []);

  return (
    <section>
      <h2>Custom agents</h2>
      {error ? <p class="error">{error}</p> : null}
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td>{a.display_name}</td>
              <td>{a.description || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
