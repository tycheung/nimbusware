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

type ChatTurnSummary = {
  turn_count?: number;
  sessions_scanned?: number;
  classifier_acceptance_rate?: number;
};

export function MetricsPage() {
  const [body, setBody] = useState<Summary | null>(null);
  const [chatTurns, setChatTurns] = useState<ChatTurnSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<Summary>("/platform/analytics/competitive-summary?limit_runs=500")
      .then(setBody)
      .catch((e) => setError(String((e as Error).message || e)));
    apiJson<ChatTurnSummary>("/platform/analytics/chat-turns?limit_sessions=500")
      .then(setChatTurns)
      .catch(() => setChatTurns(null));
  }, []);

  const m = body?.metrics || {};
  const gate = (m.slice_gate_pass_rate || {}) as Record<string, unknown>;
  const slices = (m.slices_per_completed_run || {}) as Record<string, unknown>;
  const intent = (m.intent_to_first_slice_ms || {}) as Record<string, unknown>;
  const patchIntent = (m.intent_to_first_patch_ms || {}) as Record<string, unknown>;
  const classifier = (m.classifier_acceptance_rate || {}) as Record<string, unknown>;
  const classifierDrift = (m.classifier_acceptance_drift || {}) as Record<string, unknown>;
  const stitch = (m.stitch_transplant || {}) as Record<string, unknown>;
  const research = (m.research_brief_utilization || {}) as Record<string, unknown>;
  const patchBench = m.intent_to_patch_benchmark as Record<string, unknown> | null | undefined;
  const classifierBench = m.classifier_acceptance_benchmark as
    | Record<string, unknown>
    | null
    | undefined;
  const swe = m.swe_bench as Record<string, unknown> | null | undefined;
  const factory = m.factory_weekly as Record<string, unknown> | null | undefined;
  const criticRel = m.critic_reliability as Record<string, unknown> | null | undefined;
  const policyOutcome = (m.policy_outcome || {}) as Record<string, unknown>;

  return (
    <section>
      <h2>Competitive metrics</h2>
      <p class="muted">
        Snapshot over recent runs. After Admin run detail Policy compare, gate pass rate delta appears
        below when both runs have slice gates.
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
                <td>Policy outcome (gate vs critic snapshot)</td>
                <td>
                  Gate {fmtRate(policyOutcome.slice_gate_pass_rate)} · critic FAIL{" "}
                  {fmtRate(policyOutcome.critic_fail_rate_snapshot)} (
                  {String(policyOutcome.slice_gate_sample ?? 0)} gates in sample)
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
                <td>Intent → first patch (median ms, target &lt; 3 min)</td>
                <td>
                  {typeof patchIntent.median_ms === "number"
                    ? `${Math.round(patchIntent.median_ms).toLocaleString()} ms${
                        patchIntent.meets_target === true
                          ? " ✓"
                          : patchIntent.meets_target === false
                            ? " (over target)"
                            : ""
                      }`
                    : "—"}{" "}
                  ({String(patchIntent.sample_size ?? 0)} patch runs)
                </td>
              </tr>
              <tr>
                <td>Classifier acceptance (target ≥ 70%)</td>
                <td>
                  {fmtRate(classifier.rate)} ({String(classifier.classifier_count ?? 0)} accept /{" "}
                  {String(classifier.override_count ?? 0)} override)
                  {typeof classifierDrift.delta === "number"
                    ? ` · drift ${(classifierDrift.delta * 100).toFixed(1)}pp vs snapshot`
                    : ""}
                </td>
              </tr>
              <tr>
                <td>Chat-turn analytics (store snapshot)</td>
                <td>
                  {typeof chatTurns.turn_count === "number"
                    ? `${String(chatTurns.turn_count)} turns / ${String(
                        chatTurns.sessions_scanned ?? 0,
                      )} sessions · chat rate ${fmtRate(chatTurns.classifier_acceptance_rate)}`
                    : "Load /v1/platform/analytics/chat-turns for store-backed metrics"}
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
                <td>Intent→patch benchmark (committed snapshot)</td>
                <td>
                  {patchBench
                    ? `${String(patchBench.path ?? "direct")} median ${
                        typeof patchBench.median_ms === "number"
                          ? Math.round(patchBench.median_ms).toLocaleString()
                          : "—"
                      } ms${
                        patchBench.meets_target === true
                          ? " ✓"
                          : patchBench.meets_target === false
                            ? " (over target)"
                            : ""
                      }${
                        typeof patchBench.chat_median_ms === "number"
                          ? ` · chat ${Math.round(patchBench.chat_median_ms).toLocaleString()} ms`
                          : ""
                      }`
                    : "No benchmarks/latest_intent_to_patch.json"}
                </td>
              </tr>
              <tr>
                <td>Classifier acceptance benchmark (committed snapshot)</td>
                <td>
                  {classifierBench
                    ? `rate ${fmtRate(classifierBench.rate)}${
                        classifierBench.meets_target === true
                          ? " ✓"
                          : classifierBench.meets_target === false
                            ? " (below target)"
                            : ""
                      } (${String(classifierBench.sample_size ?? 0)} samples)`
                    : "No benchmarks/latest_classifier_acceptance.json"}
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
              <tr>
                <td>Factory weekly golden</td>
                <td>
                  {factory
                    ? `${factory.skipped ? "skipped" : factory.passed ? "passed" : "failed"} (${String(
                        factory.entry_count ?? 0,
                      )} entries)`
                    : "No benchmarks/latest_factory_weekly.json"}
                </td>
              </tr>
              <tr>
                <td>Policy compare gate delta</td>
                <td>
                  {typeof policyOutcome.gate_pass_rate_delta === "number"
                    ? `${(policyOutcome.gate_pass_rate_delta * 100).toFixed(1)} pp (run B − run A)${
                        policyOutcome.last_policy_compare &&
                        typeof policyOutcome.last_policy_compare === "object"
                          ? ` · ${String(
                              (policyOutcome.last_policy_compare as Record<string, string>).run_a ||
                                "",
                            ).slice(0, 8)}… vs ${String(
                              (policyOutcome.last_policy_compare as Record<string, string>).run_b ||
                                "",
                            ).slice(0, 8)}…`
                          : ""
                      }`
                    : String(policyOutcome.hint ?? "—")}
                </td>
              </tr>
              <tr>
                <td>Critic reliability (fleet snapshot)</td>
                <td>
                  {criticRel
                    ? `FAIL rate ${String(
                        typeof criticRel.critic_fail_rate === "number"
                          ? (criticRel.critic_fail_rate as number) * 100
                          : criticRel.critic_fail_rate ?? "—",
                      )}% · ${String(criticRel.runs_scanned ?? 0)} runs`
                    : "No benchmarks/latest_critic_reliability.json"}
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
