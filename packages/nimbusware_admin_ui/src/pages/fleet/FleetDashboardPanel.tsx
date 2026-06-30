import type { FleetDashboard, FleetCombinedSearch } from "./types";

type FleetDashboardPanelProps = {
  dashboard: FleetDashboard;
  fleetQuery: string;
  fleetSearch: FleetCombinedSearch | null;
  fleetSearchBusy: boolean;
  fleetSearchError: string;
  rescanBusy: boolean;
  onFleetQuery: (q: string) => void;
  onFleetSearch: () => void;
  onRescanHardware: () => void;
  onDownloadExport: () => void;
};

export function FleetDashboardPanel({
  dashboard,
  fleetQuery,
  fleetSearch,
  fleetSearchBusy,
  fleetSearchError,
  rescanBusy,
  onFleetQuery,
  onFleetSearch,
  onRescanHardware,
  onDownloadExport,
}: FleetDashboardPanelProps) {
  return (
    <>
      {dashboard.sli_caption ? <p>{dashboard.sli_caption}</p> : null}
      {dashboard.worker_caption ? <p>{dashboard.worker_caption}</p> : null}
      <h3 data-testid="admin-fleet-mesh-panel">Fleet mesh</h3>
      <p class="muted" data-testid="admin-fleet-mesh-caption">
        Enterprise fleet overview. Session-scoped nodes and queue depth: use Session compute mesh
        below.
      </p>
      <h3>Fleet memory</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {(dashboard.memory_rows || []).map((row, i) => (
            <tr key={i}>
              <td>{row.field}</td>
              <td>{String(row.value ?? "—")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 data-testid="admin-fleet-semantic-search">Semantic fleet search</h3>
      <p class="muted">
        Substring learnings across tenant workspaces plus semantic fleet-memory hits when indexed.
      </p>
      <label>
        Query{" "}
        <input
          type="search"
          value={fleetQuery}
          data-testid="admin-fleet-search-query"
          onInput={(e) => onFleetQuery((e.target as HTMLInputElement).value)}
          placeholder="terraform rollback, sql timeout, …"
        />
      </label>{" "}
      <button
        type="button"
        class="secondary"
        data-testid="admin-fleet-search-btn"
        disabled={fleetSearchBusy || !fleetQuery.trim()}
        onClick={() => onFleetSearch()}
      >
        {fleetSearchBusy ? "Searching…" : "Search fleet"}
      </button>
      {fleetSearchError ? <p class="error">{fleetSearchError}</p> : null}
      {fleetSearch ? (
        <>
          <p class="hint">
            {fleetSearch.hit_count ?? 0} hit(s) — embedding mode:{" "}
            {fleetSearch.embedding_mode ?? "—"}
          </p>
          {(fleetSearch.learnings_hits || []).length > 0 ? (
            <>
              <h4>Workspace learnings</h4>
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Excerpt</th>
                    <th>Workspace</th>
                  </tr>
                </thead>
                <tbody>
                  {(fleetSearch.learnings_hits || []).map((row, i) => (
                    <tr key={`l-${i}`} data-testid="admin-fleet-search-learning-row">
                      <td>{row.title || row.learning_id || "—"}</td>
                      <td>{row.excerpt || "—"}</td>
                      <td>{row.workspace || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
          {(fleetSearch.memory_hits || []).length > 0 ? (
            <>
              <h4>Fleet memory (semantic)</h4>
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Excerpt</th>
                    <th>Score</th>
                    <th>Category</th>
                  </tr>
                </thead>
                <tbody>
                  {(fleetSearch.memory_hits || []).map((row, i) => (
                    <tr key={`m-${i}`} data-testid="admin-fleet-search-memory-row">
                      <td>{row.excerpt || "—"}</td>
                      <td>{row.score != null ? String(row.score) : "—"}</td>
                      <td>{row.category || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
        </>
      ) : null}
      {dashboard.archetype_fit_rows && dashboard.archetype_fit_rows.length > 0 ? (
        <>
          <h3 data-testid="admin-fleet-archetype-fit">Archetype fit</h3>
          <p class="muted">Behavioral + static rubric from benchmarks/latest_archetype_metrics.json.</p>
          <table class="data-table">
            <thead>
              <tr>
                <th>Archetype</th>
                <th>Fit score</th>
                <th>Meets target</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.archetype_fit_rows.map((row, i) => (
                <tr key={i} data-testid="admin-fleet-archetype-fit-row">
                  <td>{row.archetype}</td>
                  <td>{row.fit_score}</td>
                  <td>{row.meets_target}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
      <h3>Hardware fleet</h3>
      <p>
        <button
          type="button"
          class="secondary"
          data-testid="admin-fleet-rescan-btn"
          disabled={rescanBusy}
          onClick={onRescanHardware}
        >
          {rescanBusy ? "Rescanning…" : "Rescan fleet hosts"}
        </button>
      </p>
      <table class="data-table">
        <thead>
          <tr>
            <th>Host</th>
            <th>Tier</th>
            <th>RAM (GB)</th>
            <th>GPUs</th>
            <th>Platform</th>
            <th>Errors</th>
          </tr>
        </thead>
        <tbody>
          {(dashboard.hardware_rows || []).map((row, i) => (
            <tr key={i} data-testid="admin-fleet-hardware-row">
              <td>{String(row.host ?? "—")}</td>
              <td>{String(row.tier ?? "—")}</td>
              <td>
                {String(row.ram_available_gb ?? "—")} / {String(row.ram_total_gb ?? "—")}
              </td>
              <td>{String(row.gpu_count ?? "—")}</td>
              <td>{String(row.platform ?? "—")}</td>
              <td>{String(row.errors ?? "")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {dashboard.critic_reliability_rows && dashboard.critic_reliability_rows.length > 0 ? (
        <>
          <h3>Critic reliability</h3>
          {dashboard.critic_reliability_caption ? (
            <p>{dashboard.critic_reliability_caption}</p>
          ) : null}
          <table class="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.critic_reliability_rows.map((row, i) => (
                <tr key={i}>
                  <td>{row.metric}</td>
                  <td>{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
      <button type="button" onClick={onDownloadExport} disabled={!dashboard.export_json}>
        Export JSON
      </button>
    </>
  );
}
