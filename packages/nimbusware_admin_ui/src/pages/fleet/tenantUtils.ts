import type { TenantOption, TenantRow } from "./types";

export function tenantOptions(tenants: TenantRow[]): TenantOption[] {
  const out: TenantOption[] = [];
  for (const row of tenants) {
    const id = String(row.tenant_id || "").trim();
    const slug = String(row.slug || "").trim();
    if (!id && !slug) continue;
    const display = String(row.display_name || "").trim();
    const label = display ? `${slug || id} — ${display}` : slug || id;
    out.push({ id: id || slug, slug: slug || id, label });
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  return out;
}

export function filterTenants(tenants: TenantOption[], search: string): TenantOption[] {
  const q = search.trim().toLowerCase();
  if (!q) return tenants;
  return tenants.filter(
    (t) =>
      t.label.toLowerCase().includes(q) ||
      t.slug.toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q),
  );
}
