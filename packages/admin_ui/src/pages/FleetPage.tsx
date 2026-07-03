import { useCallback, useEffect, useState } from "preact/hooks";
import {
  apiJson,
  apiJsonEnterprise,
  enterpriseApiKey,
  resolveEnterpriseApiKeyForTenant,
  selectedEnterpriseTenantSlug,
  setEnterpriseTenantSlug,
} from "../api/client";
import { FleetAutopilotPanel } from "./fleet/FleetAutopilotPanel";
import { FleetComparePanel } from "./fleet/FleetComparePanel";
import { FleetCompliancePanel } from "./fleet/FleetCompliancePanel";
import { FleetDashboardPanel } from "./fleet/FleetDashboardPanel";
import { FleetMeshPanel } from "./fleet/FleetMeshPanel";
import { FleetTenantBar } from "./fleet/FleetTenantBar";
import { FleetTenantPoliciesPanel } from "./fleet/FleetTenantPoliciesPanel";
import { tenantOptions } from "./fleet/tenantUtils";
import type {
  FleetCombinedSearch,
  FleetCompareRow,
  FleetDashboard,
  MeshNodeRow,
  TenantOption,
  TenantRow,
} from "./fleet/types";

export function FleetPage() {
  const [dashboard, setDashboard] = useState<FleetDashboard | null>(null);
  const [tenants, setTenants] = useState<TenantOption[]>([]);
  const [tenantId, setTenantId] = useState(selectedEnterpriseTenantSlug);
  const [tenantSearch, setTenantSearch] = useState("");
  const [tenantA, setTenantA] = useState("");
  const [tenantB, setTenantB] = useState("");
  const [compareRows, setCompareRows] = useState<FleetCompareRow[]>([]);
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
  const [meshNodes, setMeshNodes] = useState<MeshNodeRow[]>([]);
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
  const [fleetQuery, setFleetQuery] = useState("");
  const [fleetSearch, setFleetSearch] = useState<FleetCombinedSearch | null>(null);
  const [fleetSearchBusy, setFleetSearchBusy] = useState(false);
  const [fleetSearchError, setFleetSearchError] = useState("");

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

  const runFleetSearch = async () => {
    const q = fleetQuery.trim();
    if (!q || !enterpriseApiKey()) {
      return;
    }
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || null;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    setFleetSearchBusy(true);
    setFleetSearchError("");
    try {
      const enc = encodeURIComponent(q);
      const headers = { "X-Nimbusware-Api-Key": key };
      const [learnings, memory] = await Promise.all([
        apiJsonEnterprise<{ hits?: FleetCombinedSearch["learnings_hits"] }>(
          `/enterprise/fleet-learnings/search?q=${enc}&k=10`,
          { headers },
        ),
        apiJsonEnterprise<{ hits?: FleetCombinedSearch["memory_hits"]; embedding_mode?: string }>(
          `/enterprise/fleet-memory/search?q=${enc}&k=10`,
          { headers },
        ).catch(() => ({ hits: [], embedding_mode: "none" })),
      ]);
      const learningsHits = learnings.hits || [];
      const memoryHits = memory.hits || [];
      setFleetSearch({
        query: q,
        embedding_mode: memory.embedding_mode,
        learnings_hits: learningsHits,
        memory_hits: memoryHits,
        hit_count: learningsHits.length + memoryHits.length,
      });
    } catch (e) {
      setFleetSearch(null);
      setFleetSearchError(String((e as Error).message || e));
    } finally {
      setFleetSearchBusy(false);
    }
  };

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
        <FleetTenantBar
          tenants={tenants}
          tenantId={tenantId}
          tenantSearch={tenantSearch}
          onTenantSearch={setTenantSearch}
          onTenantChange={onTenantChange}
        />
      ) : null}
      <button type="button" class="secondary" onClick={loadDashboard}>
        Refresh
      </button>
      {error ? <p class="error">{error}</p> : null}
      {compliance ? (
        <>
          <FleetCompliancePanel compliance={compliance} />
          <FleetTenantPoliciesPanel
            tenantId={tenantId}
            legalHold={legalHold}
            auditPolicyBusy={auditPolicyBusy}
            auditPolicyCaption={auditPolicyCaption}
            allowExternalCollab={allowExternalCollab}
            maxParticipants={maxParticipants}
            collabPolicyCaption={collabPolicyCaption}
            collabPolicyBusy={collabPolicyBusy}
            allowedApiStack={allowedApiStack}
            allowedWebStack={allowedWebStack}
            stackPolicyCaption={stackPolicyCaption}
            stackPolicyBusy={stackPolicyBusy}
            onLegalHoldChange={(enabled) => void saveLegalHold(enabled)}
            onAllowExternalCollabChange={setAllowExternalCollab}
            onMaxParticipantsChange={setMaxParticipants}
            onSaveCollabPolicy={() => void saveCollabPolicy()}
            onAllowedApiStackChange={setAllowedApiStack}
            onAllowedWebStackChange={setAllowedWebStack}
            onSaveStackPolicy={() => void saveStackPolicy()}
          />
        </>
      ) : null}
      {dashboard ? (
        <>
          <FleetDashboardPanel
            dashboard={dashboard}
            fleetQuery={fleetQuery}
            fleetSearch={fleetSearch}
            fleetSearchBusy={fleetSearchBusy}
            fleetSearchError={fleetSearchError}
            rescanBusy={rescanBusy}
            onFleetQuery={setFleetQuery}
            onFleetSearch={() => void runFleetSearch()}
            onRescanHardware={rescanFleetHardware}
            onDownloadExport={downloadExport}
          />
          {tenantId ? (
            <FleetAutopilotPanel
              policyLevel={policyLevel}
              policyCheckpoints={policyCheckpoints}
              policyCatalog={policyCatalog}
              policyCaption={policyCaption}
              enforcementMin={enforcementMin}
              enforcementMax={enforcementMax}
              enforcementCaption={enforcementCaption}
              onPolicyLevelChange={setPolicyLevel}
              onPolicyCheckpointsChange={setPolicyCheckpoints}
              onEnforcementMinChange={setEnforcementMin}
              onEnforcementMaxChange={setEnforcementMax}
              onSaveAutopilotPolicy={saveAutopilotPolicy}
              onSaveEnforcementPolicy={saveEnforcementPolicy}
            />
          ) : null}
          <FleetMeshPanel
            meshSessionId={meshSessionId}
            meshNodes={meshNodes}
            onMeshSessionIdChange={setMeshSessionId}
            onLoadNodes={loadSessionMeshNodes}
          />
          <FleetComparePanel
            tenants={tenants}
            tenantA={tenantA}
            tenantB={tenantB}
            compareRows={compareRows}
            compareCaption={compareCaption}
            compareCsv={compareCsv}
            onTenantA={setTenantA}
            onTenantB={setTenantB}
            onCompare={loadCompare}
          />
        </>
      ) : null}
    </section>
  );
}
