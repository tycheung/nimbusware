import type { MeshNodeRow } from "./types";

type FleetMeshPanelProps = {
  meshSessionId: string;
  meshNodes: MeshNodeRow[];
  onMeshSessionIdChange: (id: string) => void;
  onLoadNodes: () => void;
};

export function FleetMeshPanel({
  meshSessionId,
  meshNodes,
  onMeshSessionIdChange,
  onLoadNodes,
}: FleetMeshPanelProps) {
  return (
    <>
      <h3>Session compute mesh</h3>
      <p class="muted">Nodes registered for a collaborative chat session (share policy + delegate).</p>
      <label>
        Session ID{" "}
        <input
          type="text"
          value={meshSessionId}
          onInput={(e) => onMeshSessionIdChange((e.target as HTMLInputElement).value)}
          placeholder="chat session uuid"
          data-testid="admin-fleet-mesh-session-id"
        />
      </label>{" "}
      <button type="button" class="secondary" onClick={onLoadNodes}>
        Load nodes
      </button>
      <table class="data-table">
        <thead>
          <tr>
            <th>Node</th>
            <th>Status</th>
            <th>Share policy</th>
            <th>Delegate</th>
          </tr>
        </thead>
        <tbody>
          {meshNodes.map((row, i) => (
            <tr key={i} data-testid="admin-fleet-mesh-node-row">
              <td>{row.display_name || row.node_id || "—"}</td>
              <td>{row.status || "—"}</td>
              <td>{row.share_policy || "—"}</td>
              <td>{row.allow_host_resource_management ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
