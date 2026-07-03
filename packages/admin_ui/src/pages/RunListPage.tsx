import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";
import {
  buildRunsQuery,
  filtersFromSearch,
  syncFiltersToUrl,
  type RunListFilters,
} from "../runListCursor";

type RunSummary = {
  status?: string;
  workflow_profile?: string;
  event_count?: number;
  findings_count?: number;
};

type RunListResponse = {
  run_ids: string[];
  summaries?: Record<string, RunSummary>;
  has_more?: boolean;
  next_cursor?: string;
};

function exportCsv(runIds: string[], summaries: Record<string, RunSummary>) {
  const header = "run_id,status,workflow_profile,event_count,findings_count\n";
  const lines = runIds.map((id) => {
    const s = summaries[id] || {};
    return [id, s.status || "", s.workflow_profile || "", s.event_count ?? "", s.findings_count ?? ""].join(
      ",",
    );
  });
  const blob = new Blob([header + lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "runs-export.csv";
  a.click();
}

export function RunListPage() {
  const [filters, setFilters] = useState<RunListFilters>(() =>
    filtersFromSearch(typeof window !== "undefined" ? window.location.search : ""),
  );
  const [data, setData] = useState<RunListResponse | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const body = await apiJson<RunListResponse>(`/runs?${buildRunsQuery(filters)}`);
      setData(body);
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }, [filters]);

  useEffect(() => {
    syncFiltersToUrl(filters);
    void load();
  }, [filters, load]);

  function update(patch: Partial<RunListFilters>) {
    setFilters((f) => ({ ...f, ...patch, cursor: patch.cursor !== undefined ? patch.cursor : "" }));
  }

  const summaries = data?.summaries || {};

  return (
    <section>
      <h2>Runs</h2>
      <form
        class="filters"
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label>
          Status{" "}
          <select
            value={filters.status}
            onChange={(e) => update({ status: (e.target as HTMLSelectElement).value })}
          >
            <option value="">Any</option>
            <option value="created">created</option>
            <option value="running">running</option>
            <option value="terminal">terminal</option>
          </select>
        </label>
        <label>
          Workflow{" "}
          <input
            value={filters.workflow_profile}
            onInput={(e) => update({ workflow_profile: (e.target as HTMLInputElement).value })}
            placeholder="micro_slice"
          />
        </label>
        <label>
          Limit{" "}
          <input
            type="number"
            min={1}
            max={200}
            value={filters.limit}
            onInput={(e) => update({ limit: Number((e.target as HTMLInputElement).value) || 50 })}
          />
        </label>
        <button type="submit">Apply</button>
        <button
          type="button"
          onClick={() => data && exportCsv(data.run_ids, summaries)}
          disabled={!data?.run_ids?.length}
        >
          Export CSV
        </button>
      </form>
      {error ? <p class="error">{error}</p> : null}
      <table class="data-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Status</th>
            <th>Workflow</th>
            <th>Events</th>
          </tr>
        </thead>
        <tbody>
          {(data?.run_ids || []).map((id) => {
            const s = summaries[id] || {};
            return (
              <tr key={id}>
                <td>
                  <a href={`/v1/admin/app/runs/${id}`}>{id}</a>
                </td>
                <td>{s.status || "—"}</td>
                <td>{s.workflow_profile || "—"}</td>
                <td>{s.event_count ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div class="pagination">
        <button type="button" disabled={!filters.cursor} onClick={() => update({ cursor: "" })}>
          First page
        </button>
        <button
          type="button"
          disabled={!data?.has_more || !data?.next_cursor}
          onClick={() => update({ cursor: data?.next_cursor || "" })}
        >
          Next page
        </button>
      </div>
    </section>
  );
}
