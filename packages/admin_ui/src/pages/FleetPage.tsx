import { useCallback, useEffect, useState } from "preact/hooks";
import {
  apiJson,
  apiJsonEnterprise,
  enterpriseApiKey,
  formatCapacityMissMessage,
  formatPeelMissMessage,
  formatReadCatchMessage,
  formatWriteCatchMessage,
  getFleetMeshStatus,
  getSessionComputeStatus,
  getWorkUnitQueueDepth,
  isCapacityMiss,
  isDomainPeelMiss,
  isMemoryMiss,
  peelMissFromFetchError,
  resolveEnterpriseApiKeyForTenant,
  selectedEnterpriseTenantSlug,
  setEnterpriseTenantSlug,
  writeMissMessage,
} from "../api/client"; // sak499-d
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

function peelUnavailable(caption: string): boolean {
  return /unavailable|broker_miss/i.test(caption);
}

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
  const [meshError, setMeshError] = useState("");
  const [meshQueueDepth, setMeshQueueDepth] = useState<number | null>(null);
  const [meshVia, setMeshVia] = useState("");
  const [error, setError] = useState("");
  const [compliance, setCompliance] = useState<Record<string, unknown> | null>(null);
  const [complianceMiss, setComplianceMiss] = useState("");
  const [compareMiss, setCompareMiss] = useState(false);
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
  const [capacityPeelMiss, setCapacityPeelMiss] = useState("");
  const [memoryPeelMiss, setMemoryPeelMiss] = useState("");

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
        const rows = body.hardware_rows || [];
        const rowMiss = rows.some((r) => isCapacityMiss(r));
        const dashMiss = isCapacityMiss(body);
        if (dashMiss || rowMiss) {
          setCapacityPeelMiss(
            formatCapacityMissMessage(
              dashMiss
                ? body
                : {
                    error: "fleet hardware peel miss",
                    feature: "fleet_dashboard",
                  },
            ),
          );
        } else {
          setCapacityPeelMiss("");
        }
        // sak494-h: surface fleet_memory status peel miss on dashboard load
        const memBody = body.fleet_memory;
        if (isMemoryMiss(memBody)) {
          setMemoryPeelMiss(formatPeelMissMessage(memBody, "fleet memory unavailable"));
        } else {
          setMemoryPeelMiss("");
        }
      })
      .catch((e) => {
        const miss = peelMissFromFetchError(e);
        if (miss && isCapacityMiss(miss)) {
          setCapacityPeelMiss(formatCapacityMissMessage(miss));
          setError("");
          return;
        }
        if (miss && isMemoryMiss(miss)) {
          setMemoryPeelMiss(formatPeelMissMessage(miss, "fleet memory unavailable"));
          setError("");
          return;
        }
        setError(formatReadCatchMessage(e, "fleet dashboard unavailable"));
      });
  }, [tenantId, tenants]);

  const loadCompliance = useCallback(() => {
    if (!enterpriseApiKey()) {
      setCompliance(null);
      setComplianceMiss("");
      return;
    }
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || null;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    apiJsonEnterprise<Record<string, unknown>>("/enterprise/compliance/summary", {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setCompliance(null);
          setComplianceMiss(formatPeelMissMessage(body, "compliance summary unavailable"));
          return;
        }
        setComplianceMiss("");
        setCompliance(body);
      })
      .catch((e) => {
        setCompliance(null);
        setComplianceMiss(formatReadCatchMessage(e, "compliance summary unavailable"));
      });
  }, [tenantId, tenants]);

  useEffect(() => {
    if (!enterpriseApiKey()) {
      return;
    }
    apiJsonEnterprise<{ tenants?: TenantRow[]; via?: string; error?: string }>(
      "/enterprise/tenants",
    )
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setTenants([]);
          setError(formatPeelMissMessage(body, "tenants unavailable"));
          return;
        }
        setTenants(tenantOptions(body.tenants || []));
      })
      .catch((e) => {
        setTenants([]);
        setError(formatReadCatchMessage(e, "tenants unavailable"));
      });
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
    apiJsonEnterprise<{ legal_hold?: boolean; via?: string; error?: string }>(
      `/enterprise/audit-policy?tenant_slug=${encodeURIComponent(slug)}`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setAuditPolicyCaption(formatPeelMissMessage(body, "audit policy unavailable"));
          return;
        }
        setLegalHold(Boolean(body.legal_hold));
        setAuditPolicyCaption(`Audit policy for ${slug}`);
      })
      .catch((e) =>
        setAuditPolicyCaption(formatReadCatchMessage(e, "audit policy unavailable")),
      );
  }, [tenantId, tenants]);

  useEffect(() => {
    loadAuditPolicy();
  }, [loadAuditPolicy]);

  const saveLegalHold = async (enabled: boolean) => {
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId || "default";
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const fallback = "audit policy save unavailable";
    setAuditPolicyBusy(true);
    try {
      const body = await apiJsonEnterprise<{ via?: string; error?: string; status?: string }>(
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
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setAuditPolicyCaption(miss);
        return;
      }
      setLegalHold(enabled);
      setAuditPolicyCaption(
        enabled
          ? `Legal hold ON for ${slug} — event-store purge is blocked`
          : `Legal hold OFF for ${slug}`,
      );
      loadCompliance();
    } catch (e) {
      setAuditPolicyCaption(formatWriteCatchMessage(e, fallback));
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
    apiJsonEnterprise<{
      allow_external_collaborators?: boolean;
      max_session_participants?: number;
      via?: string;
      error?: string;
    }>(
      `/enterprise/tenants/${encodeURIComponent(tenantSlug)}/collab-policy`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setCollabPolicyCaption(formatPeelMissMessage(body, "collab policy unavailable"));
          return;
        }
        setAllowExternalCollab(Boolean(body.allow_external_collaborators));
        setMaxParticipants(body.max_session_participants ?? 20);
        setCollabPolicyCaption(`Collab guest policy for ${tenantSlug}`);
      })
      .catch((e) =>
        setCollabPolicyCaption(formatReadCatchMessage(e, "collab policy unavailable")),
      );
  }, [tenantId, tenantSlug]);

  useEffect(() => {
    loadCollabPolicy();
  }, [loadCollabPolicy]);

  const saveCollabPolicy = async () => {
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug);
    const fallback = "collab policy save unavailable";
    setCollabPolicyBusy(true);
    try {
      const body = await apiJsonEnterprise<{ via?: string; error?: string; status?: string }>(
        `/enterprise/tenants/${encodeURIComponent(tenantSlug)}/collab-policy`,
        {
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
        },
      );
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setCollabPolicyCaption(miss);
        return;
      }
      setCollabPolicyCaption(
        allowExternalCollab
          ? `External link joins allowed for ${tenantSlug}`
          : `Directory-only guests for ${tenantSlug}`,
      );
    } catch (e) {
      setCollabPolicyCaption(formatWriteCatchMessage(e, fallback));
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
    apiJsonEnterprise<{ allowed_stacks?: Record<string, string>; via?: string; error?: string }>(
      `/enterprise/tenants/${encodeURIComponent(tenantSlug)}/stack-policy`,
      { headers: { "X-Nimbusware-Api-Key": key } },
    )
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setStackPolicyCaption(formatPeelMissMessage(body, "stack policy unavailable"));
          return;
        }
        const stacks = body.allowed_stacks || {};
        setAllowedApiStack(stacks.api || "");
        setAllowedWebStack(stacks.web || "");
        setStackPolicyCaption(`Regulated stack policy for ${tenantSlug}`);
      })
      .catch((e) =>
        setStackPolicyCaption(formatReadCatchMessage(e, "stack policy unavailable")),
      );
  }, [tenantId, tenantSlug]);

  useEffect(() => {
    loadStackPolicy();
  }, [loadStackPolicy]);

  const saveStackPolicy = async () => {
    const key = resolveEnterpriseApiKeyForTenant(tenantSlug);
    const fallback = "stack policy save unavailable";
    setStackPolicyBusy(true);
    try {
      const allowed_stacks: Record<string, string> = {};
      if (allowedApiStack.trim()) allowed_stacks.api = allowedApiStack.trim();
      if (allowedWebStack.trim()) allowed_stacks.web = allowedWebStack.trim();
      const body = await apiJsonEnterprise<{ via?: string; error?: string; status?: string }>(
        `/enterprise/tenants/${encodeURIComponent(tenantSlug)}/stack-policy`,
        {
          method: "PUT",
          headers: {
            "X-Nimbusware-Api-Key": key,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ allowed_stacks }),
        },
      );
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setStackPolicyCaption(miss);
        return;
      }
      setStackPolicyCaption(`Saved stack allowlist for ${tenantSlug}`);
    } catch (e) {
      setStackPolicyCaption(formatWriteCatchMessage(e, fallback));
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
      via?: string;
      error?: string;
    }>(`/admin/ui/enterprise/fleet-autopilot-policy${q}`, {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setPolicyCaption(formatPeelMissMessage(body, "autopilot policy unavailable"));
          return;
        }
        setPolicyLevel(body.max_autopilot_level ?? 10);
        setPolicyCheckpoints((body.required_checkpoints || []).join(", "));
        setPolicyCatalog(body.checkpoint_catalog || []);
        setPolicyCaption(`Tenant policy: ${body.tenant_slug || slug}`);
      })
      .catch((e) =>
        setPolicyCaption(formatReadCatchMessage(e, "autopilot policy unavailable")),
      );
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
      via?: string;
      error?: string;
    }>(`/admin/ui/enterprise/fleet-enforcement-policy${q}`, {
      headers: { "X-Nimbusware-Api-Key": key },
    })
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setEnforcementCaption(formatPeelMissMessage(body, "enforcement policy unavailable"));
          return;
        }
        setEnforcementMin(body.min_enforcement_level ?? 0);
        setEnforcementMax(body.max_enforcement_level ?? 10);
        setEnforcementCaption(`Enforcement policy: ${body.tenant_slug || slug}`);
      })
      .catch((e) =>
        setEnforcementCaption(formatReadCatchMessage(e, "enforcement policy unavailable")),
      );
  }, [tenantId, tenants]);

  useEffect(() => {
    loadEnforcementPolicy();
  }, [loadEnforcementPolicy]);

  const loadSessionMeshNodes = useCallback(() => {
    const sid = meshSessionId.trim();
    if (!sid) {
      setMeshNodes([]);
      setMeshError("");
      setMeshQueueDepth(null);
      setMeshVia("");
      return;
    }
    // sak437-g: enterprise → fleet-mesh; else session compute status (+ queue depth).
    const key = enterpriseApiKey();
    const load = key
      ? getFleetMeshStatus(sid)
      : getSessionComputeStatus(sid).then(async (status) => {
          try {
            const q = await getWorkUnitQueueDepth(sid);
            return {
              ...status,
              queue_depth:
                typeof q.queued === "number" ? q.queued : status.queue_depth,
              via: isDomainPeelMiss(q) ? "broker_miss" : status.via,
              error: q.error || status.error,
              status:
                isDomainPeelMiss(q) || status.status === "degraded"
                  ? "degraded"
                  : status.status,
            };
          } catch (e) {
            return {
              ...status,
              via: "broker_miss",
              error: String((e as Error).message || e),
              status: "degraded",
              feature: "work_unit_queue_depth",
            };
          }
        });

    load
      .then((body) => {
        setMeshNodes((body.nodes || []) as typeof meshNodes);
        const via = body.via || "";
        setMeshVia(via);
        setMeshQueueDepth(
          typeof body.queue_depth === "number" ? body.queue_depth : null,
        );
        if (isDomainPeelMiss(body)) {
          setMeshError(String(body.error || "broker_miss: compute nodes unavailable"));
        } else {
          setMeshError("");
        }
      })
      .catch((e) => {
        const miss = peelMissFromFetchError(e);
        setMeshNodes([]);
        setMeshQueueDepth(null);
        if (miss && isDomainPeelMiss(miss)) {
          setMeshVia(String(miss.via || "broker_miss"));
          setMeshError(String(miss.error || "broker_miss: compute nodes unavailable"));
          return;
        }
        setMeshVia("broker_miss");
        setMeshError(formatReadCatchMessage(e, "broker_miss: compute nodes unavailable"));
      });
  }, [meshSessionId]);

  const saveAutopilotPolicy = async () => {
    if (!enterpriseApiKey() || !tenantId) return;
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const q = `?tenant_id=${encodeURIComponent(tenantId)}`;
    const checkpoints = policyCheckpoints
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    const fallback = "autopilot policy save unavailable";
    try {
      const body = await apiJson<{ via?: string; error?: string; status?: string }>(
        `/admin/ui/enterprise/fleet-autopilot-policy${q}`,
        {
          method: "PUT",
          headers: {
            "X-Nimbusware-Api-Key": key,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            max_autopilot_level: policyLevel,
            required_checkpoints: checkpoints,
          }),
        },
      );
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setPolicyCaption(miss);
        return;
      }
      loadAutopilotPolicy();
    } catch (e) {
      setPolicyCaption(formatWriteCatchMessage(e, fallback));
    }
  };

  const saveEnforcementPolicy = async () => {
    if (!enterpriseApiKey() || !tenantId) return;
    const slug = tenants.find((t) => t.id === tenantId)?.slug || tenantId;
    const key = resolveEnterpriseApiKeyForTenant(slug);
    const q = `?tenant_id=${encodeURIComponent(tenantId)}`;
    const fallback = "enforcement policy save unavailable";
    try {
      const body = await apiJson<{ via?: string; error?: string; status?: string }>(
        `/admin/ui/enterprise/fleet-enforcement-policy${q}`,
        {
          method: "PUT",
          headers: {
            "X-Nimbusware-Api-Key": key,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            min_enforcement_level: enforcementMin,
            max_enforcement_level: enforcementMax,
          }),
        },
      );
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setEnforcementCaption(miss);
        return;
      }
      loadEnforcementPolicy();
    } catch (e) {
      setEnforcementCaption(formatWriteCatchMessage(e, fallback));
    }
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
        apiJsonEnterprise<{
          hits?: FleetCombinedSearch["memory_hits"];
          embedding_mode?: string;
          via?: string;
          error?: string;
          feature?: string;
        }>(`/enterprise/fleet-memory/search?q=${enc}&k=10`, { headers }).catch(
          (e) =>
            peelMissFromFetchError(e) ?? {
              via: "broker_miss" as const,
              error: String((e as Error).message || e),
              feature: "fleet_memory_search",
              hits: undefined,
              embedding_mode: undefined,
            },
        ),
      ]);
      if (isDomainPeelMiss(learnings)) {
        setFleetSearchError(
          formatPeelMissMessage(learnings, "fleet learnings search unavailable"),
        );
        setFleetSearch(null);
        return;
      }
      if (isMemoryMiss(memory)) {
        setFleetSearchError(
          formatPeelMissMessage(memory, "broker_miss: fleet memory search unavailable"),
        );
        setFleetSearch(null);
        return;
      }
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
      setFleetSearchError(formatReadCatchMessage(e, "fleet search unavailable"));
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
    apiJson<{
      rows?: typeof compareRows;
      caption?: string;
      csv?: string;
      via?: string;
      error?: string;
    }>(`/admin/ui/enterprise/fleet-compare${q}`, { headers: { "X-Nimbusware-Api-Key": key } })
      .then((body) => {
        if (isDomainPeelMiss(body)) {
          setCompareRows([]);
          setCompareMiss(true);
          setCompareCaption(formatPeelMissMessage(body, "fleet compare unavailable"));
          setCompareCsv("");
          return;
        }
        setCompareMiss(false);
        setCompareRows(body.rows || []);
        setCompareCaption(body.caption || "");
        setCompareCsv(body.csv || "");
      })
      .catch((e) => {
        setCompareRows([]);
        setCompareMiss(true);
        setCompareCaption(formatReadCatchMessage(e, "fleet compare unavailable"));
        setCompareCsv("");
      });
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
    const fallback = "fleet hardware rescan unavailable";
    setRescanBusy(true);
    try {
      const key = resolveEnterpriseApiKeyForTenant(
        tenants.find((t) => t.id === tenantId)?.slug || tenantId || null,
      );
      const body = await apiJson<{
        hosts?: Record<string, unknown>[];
        capacity_source?: string;
        fit_via?: string;
        via?: string;
        status?: string;
        error?: string;
        feature?: string;
      }>("/platform/hardware/fleet/rescan", {
        method: "POST",
        headers: { "X-Nimbusware-Api-Key": key },
      });
      const miss = writeMissMessage(body, fallback);
      if (miss) {
        setCapacityPeelMiss(miss);
      } else {
        setCapacityPeelMiss("");
      }
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
      const msg = formatWriteCatchMessage(e, fallback);
      setError(msg);
      if (msg.toLowerCase().includes("capacity") || msg.toLowerCase().includes("broker")) {
        setCapacityPeelMiss(msg);
      }
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
      {compliance || complianceMiss ? (
        <>
          <FleetCompliancePanel compliance={compliance} miss={complianceMiss} />
          {compliance ? (
            <FleetTenantPoliciesPanel
              tenantId={tenantId}
              legalHold={legalHold}
              auditPolicyBusy={auditPolicyBusy}
              auditPolicyCaption={auditPolicyCaption}
              auditPolicyMiss={peelUnavailable(auditPolicyCaption)}
              allowExternalCollab={allowExternalCollab}
              maxParticipants={maxParticipants}
              collabPolicyCaption={collabPolicyCaption}
              collabPolicyMiss={peelUnavailable(collabPolicyCaption)}
              collabPolicyBusy={collabPolicyBusy}
              allowedApiStack={allowedApiStack}
              allowedWebStack={allowedWebStack}
              stackPolicyCaption={stackPolicyCaption}
              stackPolicyMiss={peelUnavailable(stackPolicyCaption)}
              stackPolicyBusy={stackPolicyBusy}
              onLegalHoldChange={(enabled) => void saveLegalHold(enabled)}
              onAllowExternalCollabChange={setAllowExternalCollab}
              onMaxParticipantsChange={setMaxParticipants}
              onSaveCollabPolicy={() => void saveCollabPolicy()}
              onAllowedApiStackChange={setAllowedApiStack}
              onAllowedWebStackChange={setAllowedWebStack}
              onSaveStackPolicy={() => void saveStackPolicy()}
            />
          ) : null}
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
            capacityPeelMiss={capacityPeelMiss}
            memoryPeelMiss={memoryPeelMiss}
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
            meshError={meshError}
            meshQueueDepth={meshQueueDepth}
            meshVia={meshVia}
            meshStatus={meshVia === "broker_miss" ? "degraded" : undefined}
            onMeshSessionIdChange={setMeshSessionId}
            onLoadNodes={loadSessionMeshNodes}
          />
          <FleetComparePanel
            tenants={tenants}
            tenantA={tenantA}
            tenantB={tenantB}
            compareRows={compareRows}
            compareCaption={compareCaption}
            compareMiss={compareMiss}
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
