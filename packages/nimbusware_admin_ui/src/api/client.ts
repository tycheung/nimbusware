export type Bootstrap = {
  api_base: string;
  edition: string;
  quick_mode?: boolean;
  admin_token_required?: boolean;
  features?: {
    enterprise_fleet_ui?: boolean;
    oidc_login_ready?: boolean;
  };
};

export const ENTERPRISE_API_KEY_KEY = "nimbusware_enterprise_api_key";
export const ENTERPRISE_TENANT_SLUG_KEY = "nimbusware_enterprise_tenant_slug";
export const ENTERPRISE_TENANT_KEYS_KEY = "nimbusware_enterprise_tenant_keys";

let bootstrap: Bootstrap = { api_base: "/v1", edition: "individual" };

export async function loadBootstrap(): Promise<Bootstrap> {
  const res = await fetch("/v1/admin/app/bootstrap.json");
  if (res.ok) {
    bootstrap = await res.json();
  }
  return bootstrap;
}

export function apiBase(): string {
  return bootstrap.api_base.replace(/\/$/, "");
}

export function adminHeaders(): Record<string, string> {
  const token = sessionStorage.getItem("nimbusware_admin_token");
  return token ? { "X-Nimbusware-Admin-Token": token } : {};
}

export function enterpriseApiKey(): string {
  return (sessionStorage.getItem(ENTERPRISE_API_KEY_KEY) || "").trim();
}

export function enterpriseApiHeaders(): Record<string, string> {
  const key = enterpriseApiKey();
  return key ? { "X-Nimbusware-Api-Key": key } : {};
}

export function setEnterpriseApiKey(value: string): void {
  const trimmed = value.trim();
  if (trimmed) {
    sessionStorage.setItem(ENTERPRISE_API_KEY_KEY, trimmed);
  } else {
    sessionStorage.removeItem(ENTERPRISE_API_KEY_KEY);
  }
}

export function selectedEnterpriseTenantSlug(): string {
  return (sessionStorage.getItem(ENTERPRISE_TENANT_SLUG_KEY) || "").trim();
}

export function setEnterpriseTenantSlug(slug: string): void {
  const trimmed = slug.trim();
  if (trimmed) {
    sessionStorage.setItem(ENTERPRISE_TENANT_SLUG_KEY, trimmed);
  } else {
    sessionStorage.removeItem(ENTERPRISE_TENANT_SLUG_KEY);
  }
}

export function resolveEnterpriseApiKeyForTenant(slug: string | null): string {
  const primary = enterpriseApiKey();
  if (!slug) {
    return primary;
  }
  try {
    const raw = sessionStorage.getItem(ENTERPRISE_TENANT_KEYS_KEY);
    if (!raw) {
      return primary;
    }
    const map = JSON.parse(raw) as Record<string, string>;
    const mapped = map[slug];
    if (typeof mapped === "string" && mapped.trim()) {
      return mapped.trim();
    }
  } catch {
    /* ignore */
  }
  return primary;
}

export async function apiJsonEnterprise<T>(path: string, init: RequestInit = {}): Promise<T> {
  const slug = selectedEnterpriseTenantSlug();
  const key = resolveEnterpriseApiKeyForTenant(slug || null);
  if (!key) {
    throw new Error("Enterprise API key required (set in sign-in panel).");
  }
  return apiJson<T>(path, {
    ...init,
    headers: {
      "X-Nimbusware-Api-Key": key,
      ...(init.headers as Record<string, string>),
    },
  });
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...adminHeaders(),
      ...(init.headers as Record<string, string>),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text.slice(0, 300)}`);
  }
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}
