import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type HardwareBody = {
  profile?: Record<string, unknown>;
  resource_governor?: Record<string, unknown>;
  models_ranked?: Array<Record<string, unknown>>;
};

type PressureEntry = {
  occurred_at?: string;
  pressure_level?: string;
  ram_used_pct?: number | null;
  pressure_reason?: string | null;
  hardware_tier?: string | null;
};

export function HardwarePage() {
  const [hw, setHw] = useState<HardwareBody | null>(null);
  const [history, setHistory] = useState<PressureEntry[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError("");
    Promise.all([
      apiJson<HardwareBody>("/platform/hardware"),
      apiJson<{ entries?: PressureEntry[] }>("/platform/analytics/pressure-history?limit=20"),
    ])
      .then(([body, hist]) => {
        setHw(body);
        setHistory(hist.entries || []);
      })
      .catch((e) => setError(String((e as Error).message || e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function rescan() {
    setBusy(true);
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
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setBusy(false);
    }
  }

  const profile = hw?.profile || {};
  const gov = hw?.resource_governor || {};

  return (
    <section>
      <h2>Hardware</h2>
      <p class="muted">
        Cached hardware profile, resource governor limits, and recent pressure events from the
        event store.
      </p>
      {error ? <p class="error">{error}</p> : null}
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
          </tbody>
        </table>
      ) : (
        !error && <p>Loading…</p>
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
