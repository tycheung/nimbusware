import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";
import { BundleOutcomePanel } from "../components/BundleOutcomePanel";

type Summary = {
  generated_at?: string;
  runs_scanned?: number;
  limit_runs?: number;
  snapshot?: boolean;
  metrics?: Record<string, Record<string, unknown>>;
};

function fmtRate(v: unknown): string {
  if (typeof v !== "number") return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function MetricsPage() {
  const [body, setBody] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<Summary>("/platform/analytics/competitive-summary?limit_runs=500")
      .then(setBody)
      .catch((e) => setError(String((e as Error).message || e)));
  }, []);

  const m = body?.metrics || {};
  const gate = (m.slice_gate_pass_rate || {}) as Record<string, unknown>;
  const slices = (m.slices_per_completed_run || {}) as Record<string, unknown>;
  const intent = (m.intent_to_first_slice_ms || {}) as Record<string, unknown>;
  const stitch = (m.stitch_transplant || {}) as Record<string, unknown>;
  const research = (m.research_brief_utilization || {}) as Record<string, unknown>;
  const swe = m.swe_bench as Record<string, unknown> | null | undefined;

  return (
    <section>
      <h2>Competitive metrics</h2>
      <p class="muted">
        Snapshot over recent runs (not a historical time series). Regenerated on each load.
        Blocking CI security tools: bandit and pip-audit (see repo docs/security-quality-gates.md).
      </p>
      {error ? <p class="error">{error}</p> : null}
      {body ? (
        <>
          <p class="muted">
            Generated {body.generated_at || "—"} · {body.runs_scanned ?? 0} runs scanned (limit{" "}
            {body.limit_runs ?? 500})
          </p>
          <table class="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Slice gate pass rate</td>
                <td>
                  {fmtRate(gate.rate)} ({String(gate.pass_count ?? 0)}/
                  {String(gate.total ?? 0)} gates)
                </td>
              </tr>
              <tr>
                <td>Mean slices per completed run</td>
                <td>
                  {typeof slices.mean_slices === "number"
                    ? slices.mean_slices.toFixed(2)
                    : "—"}{" "}
                  ({String(slices.completed_runs ?? 0)} runs)
                </td>
              </tr>
              <tr>
                <td>Intent → first slice (median ms)</td>
                <td>
                  {typeof intent.median_ms === "number"
                    ? Math.round(intent.median_ms).toLocaleString()
                    : "—"}
                </td>
              </tr>
              <tr>
                <td>Stitch transplant pass rate</td>
                <td>
                  {stitch.runs_with_stitch
                    ? `${String(stitch.transplant_pass ?? 0)} pass / ${String(
                        stitch.runs_with_stitch ?? 0,
                      )} runs with stitch`
                    : "—"}
                </td>
              </tr>
              <tr>
                <td>Research brief utilization (plan stages)</td>
                <td>
                  {fmtRate(research.rate)} ({String(research.plan_with_approved_brief ?? 0)}/
                  {String(research.plan_stage_count ?? 0)})
                </td>
              </tr>
              <tr>
                <td>SWE-bench latest</td>
                <td>
                  {swe
                    ? `pass_rate ${String(swe.pass_rate ?? "—")}`
                    : "No benchmarks/latest_swe_bench.json"}
                </td>
              </tr>
            </tbody>
          </table>
        </>
      ) : (
        !error && <p>Loading…</p>
      )}
      <BundleOutcomePanel />
    </section>
  );
}
