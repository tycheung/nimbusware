import { useCallback, useEffect, useState } from "preact/hooks";
import {
  apiJson,
  formatCapacityMissMessage,
  formatPeelMissMessage,
  formatReadCatchMessage,
  formatWriteCatchMessage,
  isCapacityMiss,
  isDomainPeelMiss,
  peelMissFromFetchError,
} from "../api/client"; // sak501-a

type HardwareBody = {
  profile?: Record<string, unknown>;
  resource_governor?: Record<string, unknown>;
  models_ranked?: Array<Record<string, unknown>>;
  capacity_source?: string;
  fit_via?: string;
  binding_id?: string;
};

type PressureEntry = {
  occurred_at?: string;
  pressure_level?: string;
  ram_used_pct?: number | null;
  pressure_reason?: string | null;
  hardware_tier?: string | null;
};

type CatalogInfo = {
  version?: number;
  model_count?: number;
  updated_at?: string;
  source?: string;
  via?: string;
  capacity_source?: string;
  error?: string;
  feature?: string;
};

export function HardwarePage() {
  const [hw, setHw] = useState<HardwareBody | null>(null);
  const [history, setHistory] = useState<PressureEntry[]>([]);
  const [catalog, setCatalog] = useState<CatalogInfo | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError("");
    Promise.all([
      apiJson<HardwareBody>("/platform/hardware"),
      apiJson<{ entries?: PressureEntry[] }>("/platform/analytics/pressure-history?limit=20"),
      apiJson<CatalogInfo>("/platform/models/catalog-info"),
    ])
      .then(([body, hist, cat]) => {
        setHw(body);
        if (isDomainPeelMiss(hist) && !isCapacityMiss(hist)) {
          setHistory([]);
          setError(formatPeelMissMessage(hist, "pressure history unavailable"));
        } else {
          setHistory(hist.entries || []);
        }
        setCatalog(cat);
      })
      .catch((e) => {
        const miss = peelMissFromFetchError(e);
        if (miss && (isCapacityMiss(miss) || isDomainPeelMiss(miss))) {
          setHw(miss as HardwareBody);
          setError("");
          return;
        }
        setError(formatReadCatchMessage(e, "hardware unavailable"));
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function rescan() {
    const fallback = "hardware rescan unavailable";
    setBusy(true);
    setError("");
    try {
      const body = await apiJson<HardwareBody>("/platform/hardware/rescan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      setHw(body);
      const hist = await apiJson<{ entries?: PressureEntry[] }>(
        "/platform/analytics/pressure-history?limit=20",
      );
      setHistory(hist.entries || []);
      const cat = await apiJson<CatalogInfo>("/platform/models/catalog-info");
      setCatalog(cat);
    } catch (e) {
      setError(formatWriteCatchMessage(e, fallback));
    } finally {
      setBusy(false);
    }
  }

  const profile = hw?.profile || {};
  const gov = hw?.resource_governor || {};
  const peelMiss = isCapacityMiss(hw) || isDomainPeelMiss(hw);
  const catalogMiss = isCapacityMiss(catalog) || isDomainPeelMiss(catalog);

  return (
    <section>
      <h2>Hardware</h2>
      <p class="muted">
        Cached hardware profile, resource governor limits, and recent pressure events from the
        event store.
      </p>
      {error ? (
        <p class="error" data-testid="admin-hw-error" role="alert">
          {error.includes("CAPACITY") || error.toLowerCase().includes("broker")
            ? `Capacity peel miss: ${error}`
            : error}
        </p>
      ) : null}
      {peelMiss ? (
        <p class="error" data-testid="admin-hw-peel-miss" role="alert">
          {isCapacityMiss(hw) ? formatCapacityMissMessage(hw) : formatPeelMissMessage(hw)}
        </p>
      ) : null}
      {catalogMiss ? (
        <p class="error" data-testid="admin-hw-catalog-miss" role="alert">
          Catalog peel miss: {formatPeelMissMessage(catalog, "broker_miss")}
        </p>
      ) : null}
      <p>
        <button type="button" onClick={rescan} disabled={busy}>
          {busy ? "Rescanning…" : "Rescan hardware"}
        </button>{" "}
        <button type="button" class="secondary" onClick={load}>
          Refresh
        </button>
      </p>
      {hw ? (
        <table class="data-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Tier</td>
              <td>{String(profile.tier ?? "—")}</td>
            </tr>
            <tr>
              <td>RAM total (GB)</td>
              <td>{String(profile.ram_total_gb ?? "—")}</td>
            </tr>
            <tr>
              <td>RAM available (GB)</td>
              <td>{String(profile.ram_available_gb ?? "—")}</td>
            </tr>
            <tr>
              <td>Max system RAM %</td>
              <td>{String(gov.max_system_ram_pct ?? "—")}</td>
            </tr>
            <tr>
              <td>Ranked models</td>
              <td>{String(hw.models_ranked?.length ?? 0)}</td>
            </tr>
            <tr>
              <td>Capacity source</td>
              <td data-testid="admin-hw-capacity-source">
                {String(hw.capacity_source ?? "—")}
              </td>
            </tr>
            <tr>
              <td>Fit via</td>
              <td data-testid="admin-hw-fit-via">{String(hw.fit_via ?? "—")}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        !error && <p>Loading…</p>
      )}
      <h3>Model catalog</h3>
      {catalog ? (
        <p data-testid="admin-catalog-info" class="muted">
          v{catalog.version ?? "—"} · {catalog.model_count ?? 0} models · source{" "}
          {catalog.source ?? "—"}
          {catalog.updated_at ? ` · updated ${catalog.updated_at}` : ""}
        </p>
      ) : (
        !error && <p class="muted">Loading catalog…</p>
      )}
      <h3>Pressure history</h3>
      {history.length ? (
        <table class="data-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Level</th>
              <th>RAM used %</th>
              <th>Tier</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {history.map((row, i) => (
              <tr key={i}>
                <td>{row.occurred_at || "—"}</td>
                <td>{row.pressure_level || "—"}</td>
                <td>{row.ram_used_pct != null ? `${row.ram_used_pct}%` : "—"}</td>
                <td>{row.hardware_tier || "—"}</td>
                <td>{row.pressure_reason || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p class="muted">No hardware.profile.detected events yet.</p>
      )}
    </section>
  );
}
