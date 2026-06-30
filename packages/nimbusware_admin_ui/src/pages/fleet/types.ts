export type FleetDashboard = {
  memory_rows?: { field: string; value: unknown }[];
  worker_caption?: string | null;
  sli_caption?: string | null;
  hardware_rows?: Record<string, unknown>[];
  export_json?: string;
  export_filename_slug?: string;
  critic_reliability?: Record<string, unknown> | null;
  critic_reliability_caption?: string | null;
  critic_reliability_rows?: { metric: string; value: string }[];
  archetype_fit_rows?: { archetype: string; fit_score: string; meets_target: string }[];
};

export type FleetCombinedSearch = {
  query?: string;
  hit_count?: number;
  embedding_mode?: string;
  learnings_hits?: { title?: string; excerpt?: string; workspace?: string; learning_id?: string }[];
  memory_hits?: { excerpt?: string; score?: number; category?: string }[];
};

export type TenantRow = { tenant_id?: string; slug?: string; display_name?: string };

export type TenantOption = { id: string; slug: string; label: string };

export type FleetCompareRow = {
  tenant: string;
  runs_scanned: string;
  gates_passed: string;
  gates_failed: string;
  ollama_p95_ms: string;
};

export type MeshNodeRow = {
  node_id?: string;
  display_name?: string;
  status?: string;
  share_policy?: string;
  allow_host_resource_management?: boolean;
};
