import type { FleetCompareRow, TenantOption } from "./types";

type FleetComparePanelProps = {
  tenants: TenantOption[];
  tenantA: string;
  tenantB: string;
  compareRows: FleetCompareRow[];
  compareCaption: string;
  compareCsv: string;
  onTenantA: (id: string) => void;
  onTenantB: (id: string) => void;
  onCompare: () => void;
};

export function FleetComparePanel({
  tenants,
  tenantA,
  tenantB,
  compareRows,
  compareCaption,
  compareCsv,
  onTenantA,
  onTenantB,
  onCompare,
}: FleetComparePanelProps) {
  return (
    <>
      <h3>Cross-tenant comparison</h3>
      <p class="muted">Compare slice gate pass/fail rates between two tenants.</p>
      {tenants.length >= 2 ? (
        <>
          <label>
            Tenant A{" "}
            <select value={tenantA} onChange={(e) => onTenantA((e.target as HTMLSelectElement).value)}>
              <option value="">Select…</option>
              {tenants.map((t) => (
                <option key={`a-${t.id}`} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>{" "}
          <label>
            Tenant B{" "}
            <select value={tenantB} onChange={(e) => onTenantB((e.target as HTMLSelectElement).value)}>
              <option value="">Select…</option>
              {tenants.map((t) => (
                <option key={`b-${t.id}`} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>{" "}
          <button
            type="button"
            class="secondary"
            onClick={onCompare}
            disabled={!tenantA || !tenantB || tenantA === tenantB}
          >
            Compare
          </button>{" "}
          <button
            type="button"
            class="secondary"
            onClick={() => {
              if (!compareCsv) return;
              const blob = new Blob([compareCsv], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "fleet_compare.csv";
              a.click();
              URL.revokeObjectURL(url);
            }}
            disabled={!compareCsv}
            data-testid="fleet-compare-csv-download"
          >
            Download CSV
          </button>
          {compareCaption ? <p>{compareCaption}</p> : null}
          {compareRows.length ? (
            <table class="data-table">
              <thead>
                <tr>
                  <th>Tenant</th>
                  <th>Runs scanned</th>
                  <th>Gates passed</th>
                  <th>Gates failed</th>
                  <th>Ollama p95 ms</th>
                </tr>
              </thead>
              <tbody>
                {compareRows.map((row, i) => (
                  <tr key={i}>
                    <td>{row.tenant}</td>
                    <td>{row.runs_scanned}</td>
                    <td>{row.gates_passed}</td>
                    <td>{row.gates_failed}</td>
                    <td>{row.ollama_p95_ms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </>
      ) : (
        <p class="muted">Need at least two tenants to compare.</p>
      )}
    </>
  );
}
