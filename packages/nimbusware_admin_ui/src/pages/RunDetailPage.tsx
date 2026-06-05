import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";
import { CriticReliabilityPanel } from "../components/CriticReliabilityPanel";
import { ProbationNoticePanel } from "../components/ProbationNoticePanel";
import { ResearchPanel } from "../components/ResearchPanel";
import { IntegrationAdapterPanel } from "../components/IntegrationAdapterPanel";
import { StitchSummaryPanel } from "../components/StitchSummaryPanel";
import { TheaterPanel } from "../components/TheaterPanel";
import { TimelineAccordion } from "../components/TimelineAccordion";

type RunDetail = {
  run_id: string;
  status?: string;
  workflow_profile?: string;
  event_count?: number;
  findings_count?: number;
  has_escalation?: boolean;
  latest_event_type?: string;
};

export function RunDetailPage({ id }: { id?: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [timeline, setTimeline] = useState<Record<string, unknown> | null>(null);
  const [findings, setFindings] = useState<Record<string, string>[]>([]);
  const [critics, setCritics] = useState<Record<string, string>[]>([]);
  const [timelineSeq, setTimelineSeq] = useState<number | null>(null);
  const [actionMsg, setActionMsg] = useState("");
  const [compareRunB, setCompareRunB] = useState("");
  const [policyDiffCaption, setPolicyDiffCaption] = useState("");
  const [policyDiffRows, setPolicyDiffRows] = useState<
    { key: string; run_a: string; run_b: string }[]
  >([]);
  const [executeRoleId, setExecuteRoleId] = useState("planner");

  useEffect(() => {
    if (!id) return;
    apiJson<RunDetail>(`/runs/${id}`).then(setRun);
    apiJson<Record<string, unknown>>(`/runs/${id}/timeline`).then(setTimeline).catch(() => setTimeline(null));
    apiJson<{ rows: Record<string, string>[] }>(`/admin/ui/runs/${id}/findings-table`)
      .then((b) => setFindings(b.rows || []))
      .catch(() => setFindings([]));
    apiJson<{ rows: Record<string, string>[] }>(`/admin/ui/runs/${id}/critic-matrix-table`)
      .then((b) => setCritics(b.rows || []))
      .catch(() => setCritics([]));
  }, [id]);

  async function lifecycle(path: string) {
    if (!id) return;
    try {
      const res = await apiJson<Record<string, string>>(`/runs/${id}/lifecycle/${path}`, { method: "POST" });
      setActionMsg(res.status || "ok");
      setRun(await apiJson(`/runs/${id}`));
    } catch (e) {
      setActionMsg(String((e as Error).message || e));
    }
  }

  async function executeRole() {
    if (!id) return;
    const roleId = executeRoleId.trim();
    if (!roleId) return;
    try {
      const res = await apiJson<Record<string, string>>(`/roles/${encodeURIComponent(roleId)}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: id }),
      });
      setActionMsg(`${res.status || "ok"}: ${res.stage_name || res.taxonomy_key || roleId}`);
      setRun(await apiJson(`/runs/${id}`));
    } catch (e) {
      setActionMsg(String((e as Error).message || e));
    }
  }

  async function comparePolicies() {
    if (!id) return;
    const other = compareRunB.trim();
    if (!other) {
      setActionMsg("Enter a run ID to compare.");
      return;
    }
    try {
      const body = await apiJson<{
        identical?: boolean;
        changed_count?: number;
        changed?: { key?: string; run_a?: unknown; run_b?: unknown }[];
      }>(`/policy/compare?run_a=${encodeURIComponent(id)}&run_b=${encodeURIComponent(other)}`);
      if (body.identical) {
        setPolicyDiffCaption("Policy snapshots are identical.");
        setPolicyDiffRows([]);
      } else {
        setPolicyDiffCaption(`${body.changed_count ?? 0} key(s) differ between runs.`);
        setPolicyDiffRows(
          (body.changed || []).map((row) => ({
            key: row.key || "",
            run_a: JSON.stringify(row.run_a ?? null),
            run_b: JSON.stringify(row.run_b ?? null),
          })),
        );
      }
      setActionMsg("");
    } catch (e) {
      setPolicyDiffCaption("");
      setPolicyDiffRows([]);
      setActionMsg(String((e as Error).message || e));
    }
  }

  async function action(path: string, body: Record<string, string>) {
    if (!id) return;
    try {
      const res = await apiJson<Record<string, string>>(`/runs/${id}/actions/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setActionMsg(res.status || "ok");
    } catch (e) {
      setActionMsg(String((e as Error).message || e));
    }
  }

  if (!id) return <p>Select a run.</p>;
  if (!run) return <p>Loading run…</p>;

  return (
    <section>
      <h2>Run {id}</h2>
      <dl class="run-summary">
        <dt>Status</dt>
        <dd>{run.status}</dd>
        <dt>Workflow</dt>
        <dd>{run.workflow_profile || "—"}</dd>
        <dt>Events</dt>
        <dd>{run.event_count}</dd>
        <dt>Findings</dt>
        <dd>{run.findings_count}</dd>
        <dt>Escalated</dt>
        <dd>{run.has_escalation ? "yes" : "no"}</dd>
        <dt>Latest event</dt>
        <dd>{run.latest_event_type || "—"}</dd>
      </dl>
      <div class="actions">
        <button type="button" onClick={() => lifecycle("start")}>
          Start
        </button>
        <button type="button" onClick={() => lifecycle("plan")}>
          Plan
        </button>
        <button type="button" onClick={() => lifecycle("verify")}>
          Verify
        </button>
        <button type="button" onClick={() => lifecycle("slice")}>
          Slice
        </button>
        <button
          type="button"
          onClick={() =>
            action("escalate", { actor_id: "admin", reason_code: "operator", notes: "from web console" })
          }
        >
          Escalate
        </button>
        <button
          type="button"
          onClick={() =>
            action("override-gate", {
              actor_id: "admin",
              reason_code: "operator",
              stage_name: "integrator.gate",
            })
          }
        >
          Override gate
        </button>
      </div>
      {actionMsg ? <p class="hint">{actionMsg}</p> : null}
      <p>
        <a href={`/v1/maker/app/#/review?run_id=${id}`} target="_blank" rel="noopener">
          Open in Maker review
        </a>
      </p>
      <h3>Theater</h3>
      <TheaterPanel runId={id} onJumpToSeq={(seq) => setTimelineSeq(seq)} />
      <h3>Timeline</h3>
      {timeline ? (
        <TimelineAccordion runId={id} timeline={timeline} highlightSeq={timelineSeq} />
      ) : (
        <p>No timeline.</p>
      )}
      <h3>Research briefs</h3>
      <ResearchPanel runId={id} />
      <h3>Stitch / transplant</h3>
      <StitchSummaryPanel runId={id} />
      <h3>Integration adapter</h3>
      <IntegrationAdapterPanel runId={id} />
      <h3>Probation notices</h3>
      <ProbationNoticePanel rows={findings} />
      <h3>Findings</h3>
      <FindingsTable rows={findings} />
      <h3>Critic matrix</h3>
      <CriticTable rows={critics} />
      <h3>Critic reliability</h3>
      <CriticReliabilityPanel runId={id} />
      <h3>Role execute (debug)</h3>
      <p class="muted">Dispatch a single producer role stage for this run (admin §6.6).</p>
      <label>
        Role UUID or taxonomy{" "}
        <input
          value={executeRoleId}
          onInput={(e) => setExecuteRoleId((e.target as HTMLInputElement).value)}
        />
      </label>
      <button type="button" onClick={() => void executeRole()}>
        Execute role
      </button>
      <h3>Policy compare</h3>
      <p class="muted">Compare frozen policy snapshots on run.created for this run vs another.</p>
      <label>
        Compare with run ID{" "}
        <input
          value={compareRunB}
          onInput={(e) => setCompareRunB((e.target as HTMLInputElement).value)}
          placeholder="other run uuid"
        />
      </label>
      <button type="button" onClick={() => void comparePolicies()}>
        Compare
      </button>
      {policyDiffCaption ? <p class="hint">{policyDiffCaption}</p> : null}
      {policyDiffRows.length ? (
        <table class="data-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>This run</th>
              <th>Other run</th>
            </tr>
          </thead>
          <tbody>
            {policyDiffRows.map((row) => (
              <tr key={row.key}>
                <td>{row.key}</td>
                <td>
                  <code>{row.run_a}</code>
                </td>
                <td>
                  <code>{row.run_b}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}

function FindingsTable({ rows }: { rows: Record<string, string>[] }) {
  if (!rows.length) return <p>No findings.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <table class="data-table">
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {cols.map((c) => (
              <td key={c}>{r[c]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CriticTable({ rows }: { rows: Record<string, string>[] }) {
  if (!rows.length) return <p>No critic verdicts.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <table class="data-table">
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {cols.map((c) => (
              <td key={c}>{r[c]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
