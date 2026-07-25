import { useEffect, useState } from "preact/hooks";
import {
  apiJson,
  formatPeelMissMessage,
  formatReadCatchMessage,
  formatWriteCatchMessage,
  isDomainPeelMiss,
  writeMissMessage,
} from "../api/client"; // sak500-c

type RegistryEntry = Record<string, { path?: string; origin?: string; badge?: string }>;

type Registry = {
  streams?: string[];
  bundles?: RegistryEntry;
  facades?: RegistryEntry;
  connectors?: RegistryEntry;
  tiers?: RegistryEntry;
};

export function StandardsMartPage() {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [error, setError] = useState("");
  const [installMsg, setInstallMsg] = useState("");

  useEffect(() => {
    apiJson<Registry & { via?: string; error?: string; status?: string }>("/standards/registry")
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setRegistry(null);
          setError(formatPeelMissMessage(body, "standards registry unavailable"));
          return;
        }
        setRegistry(body);
      })
      .catch((e) => {
        setRegistry(null);
        setError(formatReadCatchMessage(e, "standards registry unavailable"));
      });
  }, []);

  async function installBundle(bundleId: string) {
    const fallback = "standards profile update unavailable";
    setInstallMsg("");
    try {
      const body = await apiJson<{ via?: string; error?: string; status?: string }>(
        "/users/me/standards-profile/mart-default",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Mart default",
            bundles: [bundleId],
          }),
        },
      );
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setInstallMsg(miss);
        return;
      }
      setInstallMsg(`Installed ${bundleId} on your standards profile.`);
    } catch (e) {
      setInstallMsg(formatWriteCatchMessage(e, fallback));
    }
  }

  return (
    <section>
      <h2>Standards mart</h2>
      <p class="muted">Browse core and curated bundles. Install adds them to your user standards profile.</p>
      {error ? <p class="error">{error}</p> : null}
      {installMsg ? <p>{installMsg}</p> : null}
      {!registry ? <p class="loading">Loading registry…</p> : null}
      {registry ? (
        <>
          <h3>Bundles</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Origin</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {Object.entries(registry.bundles || {}).map(([id, meta]) => (
                <tr key={id}>
                  <td>{id}</td>
                  <td>{meta.origin || "—"}</td>
                  <td>
                    <button type="button" onClick={() => void installBundle(id)}>
                      Install
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Facades</h3>
          <ul>
            {Object.keys(registry.facades || {}).map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
          <h3>Connectors</h3>
          <ul>
            {Object.keys(registry.connectors || {}).map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
