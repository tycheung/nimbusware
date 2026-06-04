import { useCallback, useEffect, useState } from "preact/hooks";
import {
  apiJson,
  apiJsonEnterprise,
  enterpriseApiKey,
  resolveEnterpriseApiKeyForTenant,
  selectedEnterpriseTenantSlug,
  setEnterpriseTenantSlug,
} from "../api/client";

type FleetDashboard = {
  memory_rows?: { field: string; value: unknown }[];
  worker_caption?: string | null;
  sli_caption?: string | null;
  hardware_rows?: Record<string, unknown>[];
  export_json?: string;
  export_filename_slug?: string;
  critic_reliability?: Record<string, unknown> | null;
};

type TenantRow = { slug?: string; display_name?: string };

function tenantOptions(tenants: TenantRow[]): { slug: string; label: string }[] {
  const out: { slug: string; label: string }[] = [];
  for (const row of tenants) {
    const slug = String(row.slug || "").trim();
    if (!slug) continue;
    const display = String(row.display_name || "").trim();
    out.push({ slug, label: display ? `${slug} — ${display}` : slug });
  }
  out.sort((a, b) => a.slug.localeCompare(b.slug));
  return out;
}

export function FleetPage() {
  const [dashboard, setDashboard] = useState<FleetDashboard | null>(null);
  const [tenants, setTenants] = useState<{ slug: string; label: string }[]>([]);
  const [tenantSlug, setTenantSlug] = useState(selectedEnterpriseTenantSlug);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(() => {
    if (!enterpriseApiKey()) {
      setError("Set your Enterprise API key in the sign-in panel.");
      setDashboard(null);
      return;
    }
    const q = tenantSlug ? `?tenant_id=${encodeURIComponent(tenantSlug)}` : "";
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug || null);
    apiJson<FleetDashboard>(`/admin/ui/enterprise/fleet-dashboard${q}`, {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        setDashboard(body);
        setError("");
      })
      .catch((e) => setError(String((e as Error).message || e)));
  }, [tenantSlug]);

  useEffect(() => {
    if (!enterpriseApiKey()) {
      return;
    }
    apiJsonEnterprise<{ tenants?: TenantRow[] }>("/enterprise/tenants")
      .then((body) => setTenants(tenantOptions(body.tenants || [])))
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const onTenantChange = (slug: string) => {
    setTenantSlug(slug);
    setEnterpriseTenantSlug(slug);
  };

  const downloadExport = () => {
    if (!dashboard?.export_json) return;
    const slug = dashboard.export_filename_slug || "enterprise_fleet_dashboard";
    const blob = new Blob([dashboard.export_json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section>
      <h2>Enterprise fleet</h2>
      <p class="muted">
        Fleet memory, Ollama SLI, worker health, and hardware tiers.{" "}
        <a href="/v1/admin/app/preflight">Preflight history</a> is on the Preflight tab.
      </p>
      {tenants.length > 0 ? (
        <label class="fleet-tenant">
          Tenant{" "}
          <select
            value={tenantSlug}
            onChange={(e) => onTenantChange((e.target as HTMLSelectElement).value)}
          >
            <option value="">(primary API key)</option>
            {tenants.map((t) => (
              <option key={t.slug} value={t.slug}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <button type="button" class="secondary" onClick={loadDashboard}>
        Refresh
      </button>
      {error ? <p class="error">{error}</p> : null}
      {dashboard ? (
        <>
          {dashboard.sli_caption ? <p>{dashboard.sli_caption}</p> : null}
          {dashboard.worker_caption ? <p>{dashboard.worker_caption}</p> : null}
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
          <h3>Hardware fleet</h3>
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
                <tr key={i}>
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
          {dashboard.critic_reliability ? (
            <>
              <h3>Critic reliability</h3>
              <pre class="json-block">{JSON.stringify(dashboard.critic_reliability, null, 2)}</pre>
            </>
          ) : null}
          <button type="button" onClick={downloadExport} disabled={!dashboard.export_json}>
            Export JSON
          </button>
        </>
      ) : null}
    </section>
  );
}
