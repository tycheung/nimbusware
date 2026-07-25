import { useEffect, useState } from "preact/hooks";
import { apiJson, formatPeelMissMessage, formatReadCatchMessage, isDomainPeelMiss } from "../api/client"; // sak500-d

type Agent = { id: string; display_name: string; system_prompt: string; description?: string };

export function CustomAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ agents: Agent[]; via?: string; error?: string; status?: string }>("/custom-agents")
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setAgents([]);
          setError(formatPeelMissMessage(body, "custom agents unavailable"));
          return;
        }
        setAgents(body.agents || []);
      })
      .catch((e) => {
        setAgents([]);
        setError(formatReadCatchMessage(e, "custom agents unavailable"));
      });
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
