import { useCallback, useEffect, useState } from "preact/hooks";
import {
  apiJson,
  apiJsonEnterprise,
  enterpriseApiKey,
  resolveEnterpriseApiKeyForTenant,
  selectedEnterpriseTenantSlug,
  setEnterpriseTenantSlug,
} from "../api/client";

type FleetDashboard = {
  memory_rows?: { field: string; value: unknown }[];
  worker_caption?: string | null;
  sli_caption?: string | null;
  hardware_rows?: Record<string, unknown>[];
  export_json?: string;
  export_filename_slug?: string;
  critic_reliability?: Record<string, unknown> | null;
  critic_reliability_caption?: string | null;
  critic_reliability_rows?: { metric: string; value: string }[];
};

type TenantRow = { tenant_id?: string; slug?: string; display_name?: string };

function tenantOptions(tenants: TenantRow[]): { id: string; slug: string; label: string }[] {
  const out: { id: string; slug: string; label: string }[] = [];
  for (const row of tenants) {
    const id = String(row.tenant_id || "").trim();
    const slug = String(row.slug || "").trim();
    if (!id && !slug) continue;
    const display = String(row.display_name || "").trim();
    const label = display ? `${slug || id} — ${display}` : slug || id;
    out.push({ id: id || slug, slug: slug || id, label });
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  return out;
}

export function FleetPage() {
  const [dashboard, setDashboard] = useState<FleetDashboard | null>(null);
  const [tenants, setTenants] = useState<{ id: string; slug: string; label: string }[]>([]);
  const [tenantId, setTenantId] = useState(selectedEnterpriseTenantSlug);
  const [tenantSearch, setTenantSearch] = useState("");
  const [tenantA, setTenantA] = useState("");
  const [tenantB, setTenantB] = useState("");
  const [compareRows, setCompareRows] = useState<
    { tenant: string; runs_scanned: string; gates_passed: string; gates_failed: string; ollama_p95_ms: string }[]
  >([]);
  const [compareCaption, setCompareCaption] = useState("");
  const [compareCsv, setCompareCsv] = useState("");
  const [rescanBusy, setRescanBusy] = useState(false);
  const [policyLevel, setPolicyLevel] = useState(10);
  const [policyCheckpoints, setPolicyCheckpoints] = useState("");
  const [policyCatalog, setPolicyCatalog] = useState<string[]>([]);
  const [policyCaption, setPolicyCaption] = useState("");
  const [enforcementMin, setEnforcementMin] = useState(0);
  const [enforcementMax, setEnforcementMax] = useState(10);
  const [enforcementCaption, setEnforcementCaption] = useState("");
  const [meshSessionId, setMeshSessionId] = useState("");
  const [meshNodes, setMeshNodes] = useState<
    {
      node_id?: string;
      display_name?: string;
      status?: string;
      share_policy?: string;
      allow_host_resource_management?: boolean;
    }[]
  >([]);
  const [error, setError] = useState("");
  const [compliance, setCompliance] = useState<Record<string, unknown> | null>(null);
  const [legalHold, setLegalHold] = useState(false);
  const [auditPolicyBusy, setAuditPolicyBusy] = useState(false);
  const [auditPolicyCaption, setAuditPolicyCaption] = useState("");
  const [allowExternalCollab, setAllowExternalCollab] = useState(false);
  const [maxParticipants, setMaxParticipants] = useState(20);
  const [collabPolicyCaption, setCollabPolicyCaption] = useState("");
  const [collabPolicyBusy, setCollabPolicyBusy] = useState(false);
  const [allowedApiStack, setAllowedApiStack] = useState("");
  const [allowedWebStack, setAllowedWebStack] = useState("");
  const [stackPolicyCaption, setStackPolicyCaption] = useState("");
  const [stackPolicyBusy, setStackPolicyBusy] = useState(false);

  const loadDashboard = useCallback(() => {
    if (!enterpriseApiKey()) {
      setError("Set your Enterprise API key in the sign-in panel.");
      setDashboard(null);
      return;
    }
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
    const slug =
      tenants.find((t) => t.id === tenantId)?.slug || tenantId || null;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    apiJson<FleetDashboard>(`/admin/ui/enterprise/fleet-dashboard${q}`, {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        setDashboard(body);
        setError("");
      })
      .catch((e) => setError(String((e as Error).message || e)));
  }, [tenantId, tenants]);

  const loadCompliance = useCallback(() => {
    if (!enterpriseApiKey()) {
      setCompliance(null);
      return;
    }
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || null;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    apiJsonEnterprise<Record<string, unknown>>("/enterprise/compliance/summary", {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => setCompliance(body))
      .catch(() => setCompliance(null));
  }, [tenantId, tenants]);

  useEffect(() => {
    if (!enterpriseApiKey()) {
      return;
    }
    apiJsonEnterprise<{ tenants?: TenantRow[] }>("/enterprise/tenants")
      .then((body) => setTenants(tenantOptions(body.tenants || [])))
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    loadCompliance();
  }, [loadCompliance]);

  const loadAuditPolicy = useCallback(() => {
    if (!enterpriseApiKey()) {
      setAuditPolicyCaption("");
      return;
    }
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || "default";
    const key = resolveEnterpriseApiKeyForTenant(slug);
    apiJsonEnterprise<{ legal_hold?: boolean }>(
      `/enterprise/audit-policy?tenant_slug=${encodeURIComponent(slug)}`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        setLegalHold(Boolean(body.legal_hold));
        setAuditPolicyCaption(`Audit policy for ${slug}`);
      })
      .catch(() => setAuditPolicyCaption(""));
  }, [tenantId, tenants]);

  useEffect(() => {
    loadAuditPolicy();
  }, [loadAuditPolicy]);

  const saveLegalHold = async (enabled: boolean) => {
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || "default";
    const key = resolveEnterpriseApiKeyForTenant(slug);
    setAuditPolicyBusy(true);
    try {
      await apiJsonEnterprise(
        `/enterprise/audit-policy?tenant_slug=${encodeURIComponent(slug)}`,
        {
          method: "PUT",
          headers: {
            "X-Nimbusware-Api-Key": key,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ legal_hold: enabled, redaction_patterns: [] }),
        },
      );
      setLegalHold(enabled);
      setAuditPolicyCaption(
        enabled
          ? `Legal hold ON for ${slug} — event-store purge is blocked`
          : `Legal hold OFF for ${slug}`,
      );
      loadCompliance();
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setAuditPolicyBusy(false);
    }
  };

  const tenantSlug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || "default";

  const loadCollabPolicy = useCallback(() => {
    if (!enterpriseApiKey() || !tenantId) {
      setCollabPolicyCaption("");
      return;
    }
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug);
    apiJsonEnterprise<{ allow_external_collaborators?: boolean; max_session_participants?: number }>(
      `/enterprise/tenants/${encodeURIComponent(tenantSlug)}/collab-policy`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        setAllowExternalCollab(Boolean(body.allow_external_collaborators));
        setMaxParticipants(body.max_session_participants ?? 20);
        setCollabPolicyCaption(`Collab guest policy for ${tenantSlug}`);
      })
      .catch(() => setCollabPolicyCaption(""));
  }, [tenantId, tenantSlug]);

  useEffect(() => {
    loadCollabPolicy();
  }, [loadCollabPolicy]);

  const saveCollabPolicy = async () => {
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug);
    setCollabPolicyBusy(true);
    try {
      await apiJsonEnterprise(`/enterprise/tenants/${encodeURIComponent(tenantSlug)}/collab-policy`, {
        method: "PUT",
        headers: {
          "X-Nimbusware-Api-Key": key,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          allow_external_collaborators: allowExternalCollab,
          max_session_participants: maxParticipants,
          host_transfer_consent_hours: 24,
          default_invite_role: "session_read",
          write_may_start_runs: false,
        }),
      });
      setCollabPolicyCaption(
        allowExternalCollab
          ? `External link joins allowed for ${tenantSlug}`
          : `Directory-only guests for ${tenantSlug}`,
      );
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setCollabPolicyBusy(false);
    }
  };

  const loadStackPolicy = useCallback(() => {
    if (!enterpriseApiKey() || !tenantId) {
      setStackPolicyCaption("");
      return;
    }
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug);
    apiJsonEnterprise<{ allowed_stacks?: Record<string, string> }>(
      `/enterprise/tenants/${encodeURIComponent(tenantSlug)}/stack-policy`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        const stacks = body.allowed_stacks || {};
        setAllowedApiStack(stacks.api || "");
        setAllowedWebStack(stacks.web || "");
        setStackPolicyCaption(`Regulated stack policy for ${tenantSlug}`);
      })
      .catch(() => setStackPolicyCaption(""));
  }, [tenantId, tenantSlug]);

  useEffect(() => {
    loadStackPolicy();
  }, [loadStackPolicy]);

  const saveStackPolicy = async () => {
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug);
    setStackPolicyBusy(true);
    try {
      const allowed_stacks: Record<string, string> = {};
      if (allowedApiStack.trim()) allowed_stacks.api = allowedApiStack.trim();
      if (allowedWebStack.trim()) allowed_stacks.web = allowedWebStack.trim();
      await apiJsonEnterprise(`/enterprise/tenants/${encodeURIComponent(tenantSlug)}/stack-policy`, {
        method: "PUT",
        headers: {
          "X-Nimbusware-Api-Key": key,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ allowed_stacks }),
      });
      setStackPolicyCaption(`Saved stack allowlist for ${tenantSlug}`);
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setStackPolicyBusy(false);
    }
  };

  const loadAutopilotPolicy = useCallback(() => {
    if (!enterpriseApiKey() || !tenantId) {
      setPolicyCaption("");
      return;
    }
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const q = `?tenant_id=${encodeURIComponent(tenantId)}`;
    apiJson<{
      max_autopilot_level?: number;
      required_checkpoints?: string[];
      checkpoint_catalog?: string[];
      tenant_slug?: string;
    }>(`/admin/ui/enterprise/fleet-autopilot-policy${q}`, {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        setPolicyLevel(body.max_autopilot_level ?? 10);
        setPolicyCheckpoints((body.required_checkpoints || []).join(", "));
        setPolicyCatalog(body.checkpoint_catalog || []);
        setPolicyCaption(`Tenant policy: ${body.tenant_slug || slug}`);
      })
      .catch(() => setPolicyCaption(""));
  }, [tenantId, tenants]);

  useEffect(() => {
    loadAutopilotPolicy();
  }, [loadAutopilotPolicy]);

  const loadEnforcementPolicy = useCallback(() => {
    if (!enterpriseApiKey() || !tenantId) {
      setEnforcementCaption("");
      return;
    }
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const q = `?tenant_id=${encodeURIComponent(tenantId)}`;
    apiJson<{
      min_enforcement_level?: number;
      max_enforcement_level?: number;
      tenant_slug?: string;
    }>(`/admin/ui/enterprise/fleet-enforcement-policy${q}`, {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        setEnforcementMin(body.min_enforcement_level ?? 0);
        setEnforcementMax(body.max_enforcement_level ?? 10);
        setEnforcementCaption(`Enforcement policy: ${body.tenant_slug || slug}`);
      })
      .catch(() => setEnforcementCaption(""));
  }, [tenantId, tenants]);

  useEffect(() => {
    loadEnforcementPolicy();
  }, [loadEnforcementPolicy]);

  const loadSessionMeshNodes = useCallback(() => {
    const sid = meshSessionId.trim();
    if (!sid) {
      setMeshNodes([]);
      return;
    }
    apiJson<{ nodes?: typeof meshNodes }>(`/compute/nodes?session_id=${encodeURIComponent(sid)}`)
      .then((body) => setMeshNodes(body.nodes || []))
      .catch(() => setMeshNodes([]));
  }, [meshSessionId]);

  const saveAutopilotPolicy = () => {
    if (!enterpriseApiKey() || !tenantId) return;
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const q = `?tenant_id=${encodeURIComponent(tenantId)}`;
    const checkpoints = policyCheckpoints
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    apiJson(`/admin/ui/enterprise/fleet-autopilot-policy${q}`, {
      method: "PUT",
      headers: {
        "X-Nimbusware-Api-Key": key,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        max_autopilot_level: policyLevel,
        required_checkpoints: checkpoints,
      }),
    })
      .then(() => loadAutopilotPolicy())
      .catch((e) => setError(String((e as Error).message || e)));
  };

  const saveEnforcementPolicy = () => {
    if (!enterpriseApiKey() || !tenantId) return;
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const q = `?tenant_id=${encodeURIComponent(tenantId)}`;
    apiJson(`/admin/ui/enterprise/fleet-enforcement-policy${q}`, {
      method: "PUT",
      headers: {
        "X-Nimbusware-Api-Key": key,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        min_enforcement_level: enforcementMin,
        max_enforcement_level: enforcementMax,
      }),
    })
      .then(() => loadEnforcementPolicy())
      .catch((e) => setError(String((e as Error).message || e)));
  };

  const onTenantChange = (id: string) => {
    setTenantId(id);
    const slug = tenants.find((t) => t.id === id)?.slug || id;
    setEnterpriseTenantSlug(slug);
  };

  const filteredTenants = tenants.filter((t) => {
    const q = tenantSearch.trim().toLowerCase();
    if (!q) return true;
    return (
      t.label.toLowerCase().includes(q) ||
      t.slug.toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q)
    );
  });

  const loadCompare = useCallback(() => {
    if (!enterpriseApiKey() || !tenantA || !tenantB) {
      return;
    }
    const key = resolveEnterpriseApiKeyForTenant(
      tenants.find((t) => t.id === tenantA)?.slug || tenantA,
    );
    const q = `?tenant_a=${encodeURIComponent(tenantA)}&tenant_b=${encodeURIComponent(tenantB)}`;
    apiJson<{ rows?: typeof compareRows; caption?: string; csv?: string }>(
      `/admin/ui/enterprise/fleet-compare${q}`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        setCompareRows(body.rows || []);
        setCompareCaption(body.caption || "");
        setCompareCsv(body.csv || "");
      })
      .catch((e) => setError(String((e as Error).message || e)));
  }, [tenantA, tenantB, tenants]);

  const downloadExport = () => {
    if (!dashboard?.export_json) return;
    const slug = dashboard.export_filename_slug || "enterprise_fleet_dashboard";
    const blob = new Blob([dashboard.export_json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const rescanFleetHardware = async () => {
    if (!enterpriseApiKey()) return;
    setRescanBusy(true);
    try {
      const key = resolveEnterpriseApiKeyForTenant(
        tenants.find((t) => t.id === tenantId)?.slug || tenantId || null,
      );
      const body = await apiJson<{ hosts?: Record<string, unknown>[] }>(
        "/platform/hardware/fleet/rescan",
        {
          method: "POST",
          headers: { "X-Nimbusware-Api-Key": key },
        },
      );
      setDashboard((prev) =>
        prev
          ? {
              ...prev,
              hardware_rows: body.hosts || prev.hardware_rows,
            }
          : prev,
      );
      setError("");
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setRescanBusy(false);
    }
  };

  return (
    <section>
      <h2>Enterprise fleet</h2>
      <p class="muted">
        Fleet memory, Ollama SLI, worker health, and hardware tiers.{" "}
        <a href="/v1/admin/app/preflight">Preflight history</a> is on the Preflight tab.
      </p>
      {tenants.length > 0 ? (
        <>
          <label class="fleet-tenant">
            Tenant{" "}
            <input
              type="search"
              placeholder="Filter org directory…"
              value={tenantSearch}
              onInput={(e) => setTenantSearch((e.target as HTMLInputElement).value)}
              data-testid="admin-fleet-tenant-search"
            />
            <select
              value={tenantId}
              onChange={(e) => onTenantChange((e.target as HTMLSelectElement).value)}
              data-testid="admin-fleet-tenant-select"
            >
              <option value="">(primary API key)</option>
              {filteredTenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <details class="org-directory panel" data-testid="admin-org-directory">
            <summary>Org directory ({filteredTenants.length})</summary>
            <table class="data-table">
              <thead>
                <tr>
                  <th>Slug</th>
                  <th>Tenant id</th>
                  <th>Label</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredTenants.map((t) => (
                  <tr key={t.id}>
                    <td>{t.slug}</td>
                    <td>{t.id}</td>
                    <td>{t.label}</td>
                    <td>
                      <button type="button" class="linkish" onClick={() => onTenantChange(t.id)}>
                        Select
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      ) : null}
      <button type="button" class="secondary" onClick={loadDashboard}>
        Refresh
      </button>
      {error ? <p class="error">{error}</p> : null}
      {compliance ? (
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
                <td>{String(compliance.audit_policy?.legal_hold ?? "—")}</td>
              </tr>
            </tbody>
          </table>
          <section class="panel" data-testid="admin-fleet-audit-policy">
            <h4>Audit retention policy</h4>
            {auditPolicyCaption ? <p class="muted">{auditPolicyCaption}</p> : null}
            <label data-testid="admin-fleet-legal-hold-toggle">
              <input
                type="checkbox"
                checked={legalHold}
                disabled={auditPolicyBusy}
                onChange={(ev) => void saveLegalHold((ev.target as HTMLInputElement).checked)}
              />
              Legal hold — block event-store purge for this tenant
            </label>
            <p class="muted">
              When enabled, <code>purge_event_store_retention.py</code> skips deletes. Env{" "}
              <code>NIMBUSWARE_EVENT_STORE_LEGAL_HOLD=1</code> also blocks purge globally.
            </p>
          </section>
          <section class="panel" data-testid="admin-fleet-collab-policy">
            <h4>Collab guest policy</h4>
            {collabPolicyCaption ? <p class="muted">{collabPolicyCaption}</p> : null}
            <label data-testid="admin-fleet-allow-external-toggle">
              <input
                type="checkbox"
                checked={allowExternalCollab}
                disabled={collabPolicyBusy || !tenantId}
                onChange={(ev) => setAllowExternalCollab((ev.target as HTMLInputElement).checked)}
              />
              Allow external collaborators via invite link (ADR 023)
            </label>
            <label>
              Max session participants{" "}
              <input
                type="number"
                min={1}
                max={500}
                value={maxParticipants}
                disabled={!tenantId}
                onInput={(e) =>
                  setMaxParticipants(Number((e.target as HTMLInputElement).value) || 1)
                }
                data-testid="admin-fleet-max-participants"
              />
            </label>
            <button
              type="button"
              class="secondary"
              disabled={collabPolicyBusy || !tenantId}
              onClick={() => void saveCollabPolicy()}
              data-testid="admin-fleet-save-collab-policy"
            >
              Save collab policy
            </button>
            <p class="muted">
              When external guests are disabled, users must be added from the org directory; token
              link joins return 403.
            </p>
          </section>
          <section class="panel" data-testid="admin-fleet-stack-policy">
            <h4>Regulated stack allowlist</h4>
            {stackPolicyCaption ? <p class="muted">{stackPolicyCaption}</p> : null}
            <label>
              API stack{" "}
              <input
                type="text"
                value={allowedApiStack}
                placeholder="fastapi_python"
                disabled={!tenantId}
                onInput={(e) => setAllowedApiStack((e.target as HTMLInputElement).value)}
                data-testid="admin-fleet-stack-api"
              />
            </label>{" "}
            <label>
              Web stack{" "}
              <input
                type="text"
                value={allowedWebStack}
                placeholder="react_vite"
                disabled={!tenantId}
                onInput={(e) => setAllowedWebStack((e.target as HTMLInputElement).value)}
                data-testid="admin-fleet-stack-web"
              />
            </label>{" "}
            <button
              type="button"
              class="secondary"
              disabled={stackPolicyBusy || !tenantId}
              onClick={() => void saveStackPolicy()}
              data-testid="admin-fleet-save-stack-policy"
            >
              Save stack policy
            </button>
            <p class="muted">
              Discovery recommendations clamp to these stacks for the selected tenant (fo2344).
            </p>
          </section>
        </section>
      ) : null}
      {dashboard ? (
        <>
          {dashboard.sli_caption ? <p>{dashboard.sli_caption}</p> : null}
          {dashboard.worker_caption ? <p>{dashboard.worker_caption}</p> : null}
          <h3 data-testid="admin-fleet-mesh-panel">Fleet mesh</h3>
          <p class="muted" data-testid="admin-fleet-mesh-caption">
            Enterprise fleet overview. Session-scoped nodes and queue depth: use Session compute mesh below.
          </p>
          <h3>Fleet memory</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {(dashboard.memory_rows || []).map((row, i) => (
                <tr key={i}>
                  <td>{row.field}</td>
                  <td>{String(row.value ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Hardware fleet</h3>
          <p>
            <button
              type="button"
              class="secondary"
              data-testid="admin-fleet-rescan-btn"
              disabled={rescanBusy}
              onClick={rescanFleetHardware}
            >
              {rescanBusy ? "Rescanning…" : "Rescan fleet hosts"}
            </button>
          </p>
          <table class="data-table">
            <thead>
              <tr>
                <th>Host</th>
                <th>Tier</th>
                <th>RAM (GB)</th>
                <th>GPUs</th>
                <th>Platform</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {(dashboard.hardware_rows || []).map((row, i) => (
                <tr key={i} data-testid="admin-fleet-hardware-row">
                  <td>{String(row.host ?? "—")}</td>
                  <td>{String(row.tier ?? "—")}</td>
                  <td>
                    {String(row.ram_available_gb ?? "—")} / {String(row.ram_total_gb ?? "—")}
                  </td>
                  <td>{String(row.gpu_count ?? "—")}</td>
                  <td>{String(row.platform ?? "—")}</td>
                  <td>{String(row.errors ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {dashboard.critic_reliability_rows && dashboard.critic_reliability_rows.length > 0 ? (
            <>
              <h3>Critic reliability</h3>
              {dashboard.critic_reliability_caption ? (
                <p>{dashboard.critic_reliability_caption}</p>
              ) : null}
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.critic_reliability_rows.map((row, i) => (
                    <tr key={i}>
                      <td>{row.metric}</td>
                      <td>{row.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
          <button type="button" onClick={downloadExport} disabled={!dashboard.export_json}>
            Export JSON
          </button>
          {tenantId ? (
            <>
              <h3>Fleet autopilot policy</h3>
              <p class="muted">
                Cap max autonomy level and require checkpoints for runs in the selected tenant.
              </p>
              {policyCaption ? <p class="hint">{policyCaption}</p> : null}
              <label>
                Max autopilot level{" "}
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={policyLevel}
                  onInput={(e) => setPolicyLevel(Number((e.target as HTMLInputElement).value) || 0)}
                />
              </label>{" "}
              <label>
                Required checkpoints (comma-separated){" "}
                <input
                  value={policyCheckpoints}
                  onInput={(e) => setPolicyCheckpoints((e.target as HTMLInputElement).value)}
                  placeholder={policyCatalog.slice(0, 2).join(", ")}
                />
              </label>{" "}
              <button type="button" class="secondary" onClick={saveAutopilotPolicy}>
                Save policy
              </button>
              <h3>Fleet enforcement policy</h3>
              <p class="muted">
                Clamp per-run enforcement depth (0–10) for workspaces in the selected tenant.
              </p>
              {enforcementCaption ? <p class="hint">{enforcementCaption}</p> : null}
              <label>
                Min enforcement level{" "}
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={enforcementMin}
                  onInput={(e) => setEnforcementMin(Number((e.target as HTMLInputElement).value) || 0)}
                  data-testid="admin-fleet-enforcement-min"
                />
              </label>{" "}
              <label>
                Max enforcement level{" "}
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={enforcementMax}
                  onInput={(e) => setEnforcementMax(Number((e.target as HTMLInputElement).value) || 0)}
                  data-testid="admin-fleet-enforcement-max"
                />
              </label>{" "}
              <button
                type="button"
                class="secondary"
                onClick={saveEnforcementPolicy}
                data-testid="admin-fleet-enforcement-save"
              >
                Save enforcement policy
              </button>
            </>
          ) : null}
          <h3>Session compute mesh</h3>
          <p class="muted">Nodes registered for a collaborative chat session (share policy + delegate).</p>
          <label>
            Session ID{" "}
            <input
              type="text"
              value={meshSessionId}
              onInput={(e) => setMeshSessionId((e.target as HTMLInputElement).value)}
              placeholder="chat session uuid"
              data-testid="admin-fleet-mesh-session-id"
            />
          </label>{" "}
          <button type="button" class="secondary" onClick={loadSessionMeshNodes}>
            Load nodes
          </button>
          <table class="data-table">
            <thead>
              <tr>
                <th>Node</th>
                <th>Status</th>
                <th>Share policy</th>
                <th>Delegate</th>
              </tr>
            </thead>
            <tbody>
              {meshNodes.map((row, i) => (
                <tr key={i} data-testid="admin-fleet-mesh-node-row">
                  <td>{row.display_name || row.node_id || "—"}</td>
                  <td>{row.status || "—"}</td>
                  <td>{row.share_policy || "—"}</td>
                  <td>{row.allow_host_resource_management ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Cross-tenant comparison</h3>
          <p class="muted">Compare slice gate pass/fail rates between two tenants.</p>
          {tenants.length >= 2 ? (
            <>
              <label>
                Tenant A{" "}
                <select
                  value={tenantA}
                  onChange={(e) => setTenantA((e.target as HTMLSelectElement).value)}
                >
                  <option value="">Select…</option>
                  {tenants.map((t) => (
                    <option key={`a-${t.id}`} value={t.id}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>{" "}
              <label>
                Tenant B{" "}
                <select
                  value={tenantB}
                  onChange={(e) => setTenantB((e.target as HTMLSelectElement).value)}
                >
                  <option value="">Select…</option>
                  {tenants.map((t) => (
                    <option key={`b-${t.id}`} value={t.id}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>{" "}
              <button
                type="button"
                class="secondary"
                onClick={loadCompare}
                disabled={!tenantA || !tenantB || tenantA === tenantB}
              >
                Compare
              </button>{" "}
              <button
                type="button"
                class="secondary"
                onClick={() => {
                  if (!compareCsv) return;
                  const blob = new Blob([compareCsv], { type: "text/csv" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "fleet_compare.csv";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                disabled={!compareCsv}
                data-testid="fleet-compare-csv-download"
              >
                Download CSV
              </button>
              {compareCaption ? <p>{compareCaption}</p> : null}
              {compareRows.length ? (
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Tenant</th>
                      <th>Runs scanned</th>
                      <th>Gates passed</th>
                      <th>Gates failed</th>
                      <th>Ollama p95 ms</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareRows.map((row, i) => (
                      <tr key={i}>
                        <td>{row.tenant}</td>
                        <td>{row.runs_scanned}</td>
                        <td>{row.gates_passed}</td>
                        <td>{row.gates_failed}</td>
                        <td>{row.ollama_p95_ms}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </>
          ) : (
            <p class="muted">Need at least two tenants to compare.</p>
          )}
        </>
      ) : null}
    </section>
  );
}
