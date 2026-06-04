export type Bootstrap = {
  api_base: string;
  edition: string;
  quick_mode?: boolean;
  admin_token_required?: boolean;
};

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
