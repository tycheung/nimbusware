import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type FactoryEvidence = {
  run_id: string;
  factory_complete?: boolean;
  factory_status?: {
    tier?: string;
    ism_coverage_pct?: number;
    put_e2e_passed?: boolean;
  } | null;
  put_e2e?: { verdict?: string; flow_id?: string; detail?: string } | null;
  factory_stages?: { stage_name?: string; verdict?: string }[];
  evidence?: Record<string, unknown>;
  ism_diff?: { added?: string[]; removed?: string[]; changed?: string[] } | null;
};

export function FactoryEvidencePanel({ runId }: { runId: string }) {
  const [data, setData] = useState<FactoryEvidence | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    apiJson<FactoryEvidence>(`/runs/${runId}/factory-evidence`)
      .then((body) => {
        setData(body);
        setErr("");
      })
      .catch((e) => {
        setData(null);
        setErr(String((e as Error).message || e));
      });
  }, [runId]);

  if (err) return <p class="muted">Factory evidence unavailable.</p>;
  if (!data) return <p>Loading factory evidence…</p>;

  const status = data.factory_status;
  const exportHref = `/v1/runs/${encodeURIComponent(runId)}/factory-evidence/export`;

  return (
    <div data-testid="admin-factory-evidence-panel">
      <dl class="run-summary">
        <dt>Factory complete</dt>
        <dd>{data.factory_complete ? "yes" : "no"}</dd>
        <dt>Tier</dt>
        <dd>{status?.tier || "—"}</dd>
        <dt>ISM coverage</dt>
        <dd>{status?.ism_coverage_pct != null ? `${status.ism_coverage_pct}%` : "—"}</dd>
        <dt>PUT E2E</dt>
        <dd>
          {status?.put_e2e_passed == null
            ? "—"
            : status.put_e2e_passed
              ? "passed"
              : "failed"}
        </dd>
      </dl>
      {data.put_e2e?.flow_id ? (
        <p class="muted">
          Flow {data.put_e2e.flow_id}: {data.put_e2e.verdict || "—"} — {data.put_e2e.detail || ""}
        </p>
      ) : null}
      {data.ism_diff ? (
        <p class="muted" data-testid="admin-factory-ism-diff">
          ISM diff: +{(data.ism_diff.added || []).length} / -{(data.ism_diff.removed || []).length}{" "}
          / Δ{(data.ism_diff.changed || []).length}
        </p>
      ) : null}
      {(data.factory_stages || []).length ? (
        <ul>
          {(data.factory_stages || []).map((stage, idx) => (
            <li key={`${stage.stage_name || "stage"}-${idx}`}>
              {stage.stage_name || "stage"} — {stage.verdict || "—"}
            </li>
          ))}
        </ul>
      ) : (
        <p class="muted">No factory cadence stages recorded.</p>
      )}
      <p>
        <a href={exportHref} download data-testid="admin-factory-evidence-download">
          Download evidence zip
        </a>
      </p>
    </div>
  );
}
