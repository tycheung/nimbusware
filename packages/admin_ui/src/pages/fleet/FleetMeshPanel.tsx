import { formatPeelMissMessage, isDomainPeelMiss } from "../../api/client"; // sak500-c
import type { MeshNodeRow } from "./types";

type FleetMeshPanelProps = {
  meshSessionId: string;
  meshNodes: MeshNodeRow[];
  meshError?: string;
  meshQueueDepth?: number | null;
  meshVia?: string;
  meshStatus?: string;
  onMeshSessionIdChange: (id: string) => void;
  onLoadNodes: () => void;
};

export function FleetMeshPanel({
  meshSessionId,
  meshNodes,
  meshError,
  meshQueueDepth,
  meshVia,
  meshStatus,
  onMeshSessionIdChange,
  onLoadNodes,
}: FleetMeshPanelProps) {
  const meshMiss = isDomainPeelMiss({
    via: meshVia,
    status: meshStatus,
    error: meshError,
  });
  return (
    <>
      <h3>Session compute mesh</h3>
      <p class="muted">Nodes registered for a collaborative chat session (share policy + delegate).</p>
      {meshMiss ? (
        <p class="error" data-testid="admin-fleet-mesh-peel-miss" role="alert">
          {formatPeelMissMessage(
            {
              via: meshVia,
              status: meshStatus,
              error: meshError,
              feature: "session_compute",
            },
            "broker_miss: compute nodes unavailable",
          )}
          {" (feature=session_compute · status=degraded)"}
        </p>
      ) : meshError ? (
        <p class="error" data-testid="admin-fleet-mesh-error" role="alert">
          {formatPeelMissMessage(
            { via: meshVia, status: meshStatus, error: meshError, feature: "session_compute" },
            meshError,
          )}
        </p>
      ) : null}
      {!meshError && meshVia && !meshMiss && meshNodes.length === 0 ? (
        <p class="muted" data-testid="admin-fleet-mesh-empty">
          No nodes for this session (broker ok, empty list — not a peel miss).
        </p>
      ) : null}
      {meshVia || meshQueueDepth != null ? (
        <p class="muted" data-testid="admin-fleet-mesh-status">
          via={meshVia || "—"}
          {meshQueueDepth != null ? ` · queue_depth=${meshQueueDepth}` : ""}
          {meshMiss ? " · status=degraded" : ""}
        </p>
      ) : null}
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
