type FleetCompliancePanelProps = {
  compliance: Record<string, unknown>;
};

export function FleetCompliancePanel({ compliance }: FleetCompliancePanelProps) {
  return (
    <section class="panel" data-testid="admin-fleet-compliance">
      <h3>Compliance summary</h3>
      <table class="data-table">
        <tbody>
          <tr>
            <td>Audit retention (days)</td>
            <td>{String(compliance.audit_retention_days ?? "—")}</td>
          </tr>
          <tr>
            <td>IAM actions indexed</td>
            <td>{String(compliance.iam_action_count ?? "—")}</td>
          </tr>
          <tr>
            <td>Event rows</td>
            <td>{String(compliance.event_row_count ?? "—")}</td>
          </tr>
          <tr>
            <td>Tenants</td>
            <td>{String(compliance.tenant_count ?? "—")}</td>
          </tr>
          <tr>
            <td>Gate pass rate</td>
            <td>
              {compliance.gate_pass_rate != null
                ? `${Math.round(Number(compliance.gate_pass_rate) * 100)}%`
                : "—"}
            </td>
          </tr>
          <tr>
            <td>Mean slices / completed run</td>
            <td>{String(compliance.mean_slices_per_run ?? "—")}</td>
          </tr>
          <tr>
            <td>Slice size histogram</td>
            <td>
              {compliance.slice_size_histogram
                ? JSON.stringify(compliance.slice_size_histogram)
                : "—"}
            </td>
          </tr>
          <tr>
            <td>Commit stage events</td>
            <td>{String(compliance.commit_stage_events ?? "—")}</td>
          </tr>
          <tr>
            <td>Last event at</td>
            <td>{String(compliance.last_event_at ?? "—")}</td>
          </tr>
          <tr>
            <td>Legal hold</td>
            <td>{String((compliance.audit_policy as Record<string, unknown> | undefined)?.legal_hold ?? "—")}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
