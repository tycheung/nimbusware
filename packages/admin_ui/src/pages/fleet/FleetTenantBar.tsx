import type { TenantOption } from "./types";

type FleetTenantBarProps = {
  tenants: TenantOption[];
  tenantId: string;
  tenantSearch: string;
  onTenantSearch: (value: string) => void;
  onTenantChange: (id: string) => void;
};

export function FleetTenantBar({
  tenants,
  tenantId,
  tenantSearch,
  onTenantSearch,
  onTenantChange,
}: FleetTenantBarProps) {
  const q = tenantSearch.trim().toLowerCase();
  const filteredTenants = q
    ? tenants.filter(
        (t) =>
          t.label.toLowerCase().includes(q) ||
          t.slug.toLowerCase().includes(q) ||
          t.id.toLowerCase().includes(q),
      )
    : tenants;

  return (
    <>
      <label class="fleet-tenant">
        Tenant{" "}
        <input
          type="search"
          placeholder="Filter org directory…"
          value={tenantSearch}
          onInput={(e) => onTenantSearch((e.target as HTMLInputElement).value)}
          data-testid="admin-fleet-tenant-search"
        />
        <select
          value={tenantId}
          onChange={(e) => onTenantChange((e.target as HTMLSelectElement).value)}
          data-testid="admin-fleet-tenant-select"
        >
          <option value="">(primary API key)</option>
          {filteredTenants.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
      </label>
      <details class="org-directory panel" data-testid="admin-org-directory">
        <summary>Org directory ({filteredTenants.length})</summary>
        <table class="data-table">
          <thead>
            <tr>
              <th>Slug</th>
              <th>Tenant id</th>
              <th>Label</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filteredTenants.map((t) => (
              <tr key={t.id}>
                <td>{t.slug}</td>
                <td>{t.id}</td>
                <td>{t.label}</td>
                <td>
                  <button type="button" class="linkish" onClick={() => onTenantChange(t.id)}>
                    Select
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}
