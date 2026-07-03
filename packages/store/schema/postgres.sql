-- Nimbusware PostgreSQL bootstrap (greenfield, single file).
-- Platform tables: nimbusware_* (IAM, projects, operator config).
-- Nimbusware agent tables: event_store, nimbusware_memory_*, nimbusware_bundle_outcome, nimbusware_roles_registry.
-- Apply to an empty database: psql "$NIMBUSWARE_DATABASE_URL" -v ON_ERROR_STOP=1 -f postgres.sql
-- Lockstep with agent_core.models.EventType (see nimbusware_store.allowed_types.allowed_event_type_values).

-- =============================================================================
-- nimbusware_tenant + nimbusware_api_key (Enterprise IAM, fo201)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_tenant (
  tenant_id UUID PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO nimbusware_tenant (tenant_id, slug, display_name) VALUES
  ('00000000-0000-4000-8000-000000000001'::uuid, 'default', 'Default (Individual)')
ON CONFLICT (tenant_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS nimbusware_api_key (
  key_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id) ON DELETE CASCADE,
  key_prefix TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL DEFAULT '',
  role_taxonomy_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
  api_scopes JSONB NOT NULL DEFAULT '["maker_user"]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ NULL,
  CHECK (jsonb_typeof(role_taxonomy_keys) = 'array'),
  CHECK (jsonb_typeof(api_scopes) = 'array')
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_api_key_tenant
  ON nimbusware_api_key (tenant_id);

ALTER TABLE nimbusware_api_key
  ADD COLUMN IF NOT EXISTS api_scopes JSONB NOT NULL DEFAULT '["maker_user"]'::jsonb;

-- =============================================================================
-- nimbusware_project (Maker product, fo301)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_project (
  project_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  name TEXT NOT NULL,
  workspace_path TEXT NOT NULL,
  template TEXT NOT NULL DEFAULT 'attach'
    CHECK (template IN ('greenfield', 'attach')),
  default_workflow_profile TEXT NOT NULL DEFAULT 'micro_slice',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_project_tenant
  ON nimbusware_project (tenant_id, created_at DESC);

-- =============================================================================
-- nimbusware_user (Track B collaborative chat, fo1510)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_user (
  user_id UUID PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL DEFAULT '',
  is_owner BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_user_username
  ON nimbusware_user (LOWER(username));

-- =============================================================================
-- nimbusware_chat_session / nimbusware_chat_turn (Maker congruent chat, §20.28)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_chat_session (
  session_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  project_id UUID NOT NULL REFERENCES nimbusware_project(project_id) ON DELETE CASCADE,
  title TEXT NULL,
  root_turn_id UUID NULL,
  active_leaf_turn_id UUID NULL,
  last_classification JSONB NULL,
  work_type_override TEXT NULL,
  run_id UUID NULL,
  campaign_id UUID NULL,
  host_user_id UUID NULL REFERENCES nimbusware_user(user_id),
  workload_distribution TEXT NOT NULL DEFAULT 'host_only'
    CHECK (workload_distribution IN ('host_only', 'manual_claim', 'auto_share', 'auto_optimize')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (last_classification IS NULL OR jsonb_typeof(last_classification) = 'object'),
  CHECK (jsonb_typeof(metadata) = 'object')
);

ALTER TABLE nimbusware_chat_session
  ADD COLUMN IF NOT EXISTS host_user_id UUID NULL REFERENCES nimbusware_user(user_id);

ALTER TABLE nimbusware_chat_session
  ADD COLUMN IF NOT EXISTS workload_distribution TEXT NOT NULL DEFAULT 'host_only';

ALTER TABLE nimbusware_chat_session
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

-- =============================================================================
-- nimbusware_chat_participant / nimbusware_chat_invite (Track B fo1520)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_chat_participant (
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES nimbusware_user(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('session_read', 'session_write', 'session_admin')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_participant_user
  ON nimbusware_chat_participant (user_id, joined_at DESC);

ALTER TABLE nimbusware_chat_participant
  ADD COLUMN IF NOT EXISTS user_discipline TEXT NULL;

CREATE TABLE IF NOT EXISTS nimbusware_chat_invite (
  invite_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('session_read', 'session_write', 'session_admin')),
  expires_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL REFERENCES nimbusware_user(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  consumed_at TIMESTAMPTZ NULL
);

ALTER TABLE nimbusware_chat_invite
  ADD COLUMN IF NOT EXISTS recommended_discipline TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_invite_session
  ON nimbusware_chat_invite (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_session_project
  ON nimbusware_chat_session (project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS nimbusware_chat_turn (
  turn_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  parent_turn_id UUID NULL,
  ordinal INT NOT NULL,
  role TEXT NOT NULL CHECK (role IN (
    'user', 'classifier', 'work_type_switch', 'run_status', 'theater', 'system'
  )),
  text TEXT NOT NULL DEFAULT '',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  work_type TEXT NULL,
  work_type_source TEXT NULL,
  run_id UUID NULL,
  campaign_id UUID NULL,
  event_seq BIGINT NULL,
  posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(payload) = 'object'),
  FOREIGN KEY (parent_turn_id) REFERENCES nimbusware_chat_turn(turn_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_turn_session
  ON nimbusware_chat_turn (session_id, ordinal ASC);

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_turn_parent
  ON nimbusware_chat_turn (session_id, parent_turn_id);

-- =============================================================================
-- event_store (Nimbusware agent append-only run events, plan §19.2)
-- =============================================================================
CREATE TABLE IF NOT EXISTS event_store (
  store_seq BIGSERIAL NOT NULL,
  event_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  run_id UUID NOT NULL,
  stage_id UUID NULL,
  task_id UUID NULL,
  event_type TEXT NOT NULL,
  event_version INT NOT NULL DEFAULT 1,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_role TEXT NULL,
  model_id TEXT NULL,
  correlation_id UUID NULL,
  causation_id UUID NULL,
  payload JSONB NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  CHECK (jsonb_typeof(payload) = 'object'),
  CONSTRAINT event_store_type_allowed CHECK (event_type IN (
    'run.created', 'run.started', 'run.failed', 'run.completed', 'run.escalated',
    'model.preflight.started', 'model.preflight.passed', 'model.preflight.failed',
    'model.selected.primary', 'model.selected.fallback',
    'stage.started', 'stage.blocked', 'stage.passed', 'stage.failed',
    'critic.verdict.emitted',
    'finding.created', 'finding.routed', 'finding.closed',
    'gate.decision.emitted', 'gate.overridden',
    'persona.shelf.updated',
    'self_refinement.loop.signalled',
    'memory.indexed',
    'memory.retrieval.emitted',
    'research.brief.emitted',
    'research.brief.approved',
    'research.brief.rejected',
    'research.pattern.indexed',
    'domain.critic.proposed',
    'stitch.license.checked',
    'stitch.dependency.checked',
    'stitch.plan.emitted',
    'stitch.applied',
    'stitch.failed',
    'hardware.profile.detected',
    'resource.pressure.warn',
    'campaign.created',
    'campaign.completed',
    'campaign.failed',
    'campaign.paused',
    'delivery_backlog.generated',
    'delivery_backlog.revised',
    'epic.status.changed',
    'slice.queued',
    'slice.deferred',
    'maintenance.refactor.started',
    'maintenance.refactor.passed',
    'maintenance.architecture.started',
    'maintenance.architecture.passed',
    'completion.evaluated',
    'model.binding.overridden',
    'workload.role_claimed',
    'workload.role_released'
  ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_store_store_seq ON event_store(store_seq);
CREATE INDEX IF NOT EXISTS idx_event_store_run_seq ON event_store(run_id, store_seq);
CREATE INDEX IF NOT EXISTS idx_event_store_tenant_run
  ON event_store (tenant_id, run_id, store_seq);

ALTER TABLE event_store ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS event_store_tenant_isolation ON event_store;
CREATE POLICY event_store_tenant_isolation ON event_store
  FOR ALL
  USING (
    tenant_id = NULLIF(current_setting('nimbusware.tenant_id', true), '')::uuid
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('nimbusware.tenant_id', true), '')::uuid
  );

CREATE OR REPLACE FUNCTION prevent_event_store_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'event_store is append-only; updates/deletes are not allowed';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_event_store_no_update ON event_store;
CREATE TRIGGER trg_event_store_no_update
BEFORE UPDATE ON event_store
FOR EACH ROW EXECUTE FUNCTION prevent_event_store_mutation();

DROP TRIGGER IF EXISTS trg_event_store_no_delete ON event_store;
CREATE TRIGGER trg_event_store_no_delete
BEFORE DELETE ON event_store
FOR EACH ROW EXECUTE FUNCTION prevent_event_store_mutation();

CREATE INDEX IF NOT EXISTS idx_event_store_run_time
  ON event_store(run_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_event_store_stage_time
  ON event_store(stage_id, occurred_at)
  WHERE stage_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_event_store_type_time
  ON event_store(event_type, occurred_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_store_correlation_unique
  ON event_store(correlation_id, event_type)
  WHERE correlation_id IS NOT NULL;

-- =============================================================================
-- run_projection (read-only dashboard projection, plan §19.3, §14 #7)
-- =============================================================================
CREATE OR REPLACE VIEW run_projection AS
SELECT
  e.run_id,
  COUNT(*)::bigint AS event_count,
  MAX(e.store_seq) AS head_store_seq,
  BOOL_OR(e.event_type = 'run.escalated') AS has_escalation,
  SUM((e.event_type = 'finding.created')::int)::bigint AS findings_count
FROM event_store e
GROUP BY e.run_id;

-- =============================================================================
-- nimbusware_roles_registry (Nimbusware agent role taxonomy, plan §5)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_roles_registry (
  taxonomy_key TEXT PRIMARY KEY,
  role_id UUID NOT NULL,
  display_name TEXT NOT NULL DEFAULT ''
);

INSERT INTO nimbusware_roles_registry (taxonomy_key, role_id, display_name) VALUES
  ('planner', '11111111-1111-4111-8111-111111111101'::uuid, 'Planner'),
  ('product_reference_critic', '22222222-2222-4222-8222-222222222202'::uuid, 'Product Reference Critic'),
  ('domain_critic', '33333333-3333-4333-8333-333333333303'::uuid, 'Domain Critic'),
  ('backend_writer', '44444444-4444-4444-8444-444444444404'::uuid, 'Backend Writer'),
  ('test_writer', '55555555-5555-4555-8555-555555555505'::uuid, 'Test Writer'),
  ('domain_researcher', '12121212-1212-4212-8212-121212121201'::uuid, 'Domain Researcher'),
  ('code_researcher', '13131313-1313-4313-8313-131313131301'::uuid, 'Code Researcher'),
  ('stitcher', '14141414-1414-4414-8414-141414141401'::uuid, 'Stitcher')
ON CONFLICT (taxonomy_key) DO NOTHING;

-- =============================================================================
-- nimbusware_config_document (operator config authority, plan §19.5)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_config_document (
  namespace TEXT NOT NULL,
  document_key TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  content JSONB NOT NULL,
  content_sha256_16 TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(content) = 'object'),
  PRIMARY KEY (namespace, document_key)
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_config_document_ns
  ON nimbusware_config_document (namespace);

CREATE OR REPLACE FUNCTION notify_nimbusware_config_document_change()
RETURNS TRIGGER AS $$
DECLARE
  payload text;
BEGIN
  payload := json_build_object(
    'type', 'config.document.updated',
    'namespace', NEW.namespace,
    'document_key', NEW.document_key,
    'version', NEW.version
  )::text;
  PERFORM pg_notify('nimbusware_config_document', payload);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_nimbusware_config_document_notify ON nimbusware_config_document;
CREATE TRIGGER trg_nimbusware_config_document_notify
AFTER INSERT OR UPDATE ON nimbusware_config_document
FOR EACH ROW EXECUTE FUNCTION notify_nimbusware_config_document_change();

-- =============================================================================
-- nimbusware_memory_* (Nimbusware agent Phase 4 repo-scoped retrieval index, fo160)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_memory_index_generation (
  generation_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  org_scope_hash TEXT NOT NULL,
  repo_scope_hash TEXT NOT NULL,
  embedding_mode TEXT NOT NULL,
  embedding_model_id TEXT NOT NULL,
  chunk_count INT NOT NULL DEFAULT 0,
  manifest_relpath TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_memory_generation_scope
  ON nimbusware_memory_index_generation (repo_scope_hash, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nimbusware_memory_generation_fleet
  ON nimbusware_memory_index_generation (tenant_id, org_scope_hash, created_at DESC);

CREATE TABLE IF NOT EXISTS nimbusware_memory_chunk (
  chunk_id UUID PRIMARY KEY,
  generation_id UUID NOT NULL REFERENCES nimbusware_memory_index_generation(generation_id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  org_scope_hash TEXT NOT NULL,
  repo_scope_hash TEXT NOT NULL,
  run_id UUID NOT NULL,
  source_event_type TEXT NOT NULL,
  source_store_seq BIGINT,
  finding_id UUID,
  category TEXT,
  severity TEXT,
  excerpt TEXT NOT NULL,
  embedding_model_id TEXT NOT NULL,
  embedding_dim INT NOT NULL,
  embedding_vector JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(embedding_vector) = 'array')
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_memory_chunk_scope_run
  ON nimbusware_memory_chunk (repo_scope_hash, run_id);

CREATE INDEX IF NOT EXISTS idx_nimbusware_memory_chunk_fleet
  ON nimbusware_memory_chunk (tenant_id, org_scope_hash, run_id);

ALTER TABLE nimbusware_memory_index_generation ENABLE ROW LEVEL SECURITY;
ALTER TABLE nimbusware_memory_chunk ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS nimbusware_memory_generation_tenant ON nimbusware_memory_index_generation;
CREATE POLICY nimbusware_memory_generation_tenant ON nimbusware_memory_index_generation
  FOR ALL
  USING (
    tenant_id = NULLIF(current_setting('nimbusware.tenant_id', true), '')::uuid
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('nimbusware.tenant_id', true), '')::uuid
  );

DROP POLICY IF EXISTS nimbusware_memory_chunk_tenant ON nimbusware_memory_chunk;
CREATE POLICY nimbusware_memory_chunk_tenant ON nimbusware_memory_chunk
  FOR ALL
  USING (
    tenant_id = NULLIF(current_setting('nimbusware.tenant_id', true), '')::uuid
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('nimbusware.tenant_id', true), '')::uuid
  );

CREATE INDEX IF NOT EXISTS idx_nimbusware_memory_chunk_generation
  ON nimbusware_memory_chunk (generation_id);

-- =============================================================================
-- nimbusware_bundle_outcome (Nimbusware agent Phase 4 bundle usage memory, fo170)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_bundle_outcome (
  outcome_id UUID PRIMARY KEY,
  run_id UUID NOT NULL,
  bundle_id TEXT NOT NULL,
  workflow_profile TEXT,
  project_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  integrator_score DOUBLE PRECISION,
  verdict TEXT NOT NULL,
  source_store_seq BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(project_tags) = 'array')
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_bundle_outcome_bundle
  ON nimbusware_bundle_outcome (bundle_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nimbusware_bundle_outcome_run
  ON nimbusware_bundle_outcome (run_id, created_at DESC);

-- =============================================================================
-- nimbusware_provider_connection (v1.2 Model Hub API vault — Track C2)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_provider_connection (
  connection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT,
  user_id TEXT NOT NULL DEFAULT '',
  provider_id TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  connection_kind TEXT NOT NULL DEFAULT 'api_key'
    CHECK (connection_kind IN ('api_key', 'subscription')),
  base_url TEXT,
  default_model_id TEXT,
  secret_blob BYTEA,
  last_probe_at TIMESTAMPTZ,
  last_probe_ok BOOLEAN,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_provider_connection_user
  ON nimbusware_provider_connection (user_id, provider_id);

CREATE INDEX IF NOT EXISTS idx_nimbusware_provider_connection_tenant
  ON nimbusware_provider_connection (tenant_id)
  WHERE tenant_id IS NOT NULL;

-- =============================================================================
-- nimbusware_compute_node / nimbusware_work_unit (v1.2 compute mesh — Track D1)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_compute_node (
  node_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  session_id UUID NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE SET NULL,
  user_id TEXT NOT NULL DEFAULT '',
  display_name TEXT NOT NULL DEFAULT '',
  host_label TEXT NOT NULL DEFAULT '',
  base_url TEXT NOT NULL DEFAULT '',
  capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
  share_policy TEXT NOT NULL DEFAULT 'off'
    CHECK (share_policy IN ('off', 'claim_only', 'managed_by_host', 'full_auto')),
  allow_host_resource_management BOOLEAN NOT NULL DEFAULT FALSE,
  last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (status IN ('unknown', 'online', 'degraded', 'offline')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(capabilities) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_compute_node_session
  ON nimbusware_compute_node (session_id, last_heartbeat_at DESC)
  WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_nimbusware_compute_node_tenant_status
  ON nimbusware_compute_node (tenant_id, status, last_heartbeat_at DESC);

CREATE TABLE IF NOT EXISTS nimbusware_work_unit (
  work_unit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  run_id UUID NOT NULL,
  session_id UUID NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE SET NULL,
  node_id UUID NULL REFERENCES nimbusware_compute_node(node_id) ON DELETE SET NULL,
  stage_name TEXT NOT NULL,
  agent_role TEXT NOT NULL DEFAULT '',
  executor_user_id TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'assigned', 'running', 'ok', 'failed', 'timeout', 'cancelled')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  result JSONB NULL,
  assigned_at TIMESTAMPTZ NULL,
  completed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(payload) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_work_unit_session_status
  ON nimbusware_work_unit (session_id, status, created_at ASC)
  WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_nimbusware_work_unit_node_status
  ON nimbusware_work_unit (node_id, status)
  WHERE node_id IS NOT NULL;

-- =============================================================================
-- Conversation library (Track B8 — folders, groups, access grants)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_chat_folder (
  folder_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  project_id UUID NOT NULL REFERENCES nimbusware_project(project_id) ON DELETE CASCADE,
  parent_folder_id UUID NULL REFERENCES nimbusware_chat_folder(folder_id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  owner_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_folder_project
  ON nimbusware_chat_folder (project_id, name);

ALTER TABLE nimbusware_chat_session
  ADD COLUMN IF NOT EXISTS folder_id UUID NULL;

ALTER TABLE nimbusware_chat_session
  ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS nimbusware_user_group (
  group_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  name TEXT NOT NULL,
  owner_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, name)
);

CREATE TABLE IF NOT EXISTS nimbusware_user_group_member (
  group_id UUID NOT NULL REFERENCES nimbusware_user_group(group_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES nimbusware_user(user_id) ON DELETE CASCADE,
  PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS nimbusware_chat_access_grant (
  grant_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL DEFAULT '00000000-0000-4000-8000-000000000001'::uuid
    REFERENCES nimbusware_tenant(tenant_id),
  grantee_type TEXT NOT NULL CHECK (grantee_type IN ('user', 'group')),
  grantee_user_id UUID NULL REFERENCES nimbusware_user(user_id) ON DELETE CASCADE,
  grantee_group_id UUID NULL REFERENCES nimbusware_user_group(group_id) ON DELETE CASCADE,
  scope_type TEXT NOT NULL CHECK (scope_type IN ('folder', 'tag', 'session')),
  folder_id UUID NULL REFERENCES nimbusware_chat_folder(folder_id) ON DELETE CASCADE,
  tag TEXT NULL,
  session_id UUID NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  participant_role TEXT NOT NULL DEFAULT 'session_read'
    CHECK (participant_role IN ('session_read', 'session_write', 'session_admin')),
  created_by UUID NOT NULL REFERENCES nimbusware_user(user_id),
  expires_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_access_grant_folder
  ON nimbusware_chat_access_grant (folder_id) WHERE folder_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_nimbusware_chat_access_grant_session
  ON nimbusware_chat_access_grant (session_id) WHERE session_id IS NOT NULL;

-- =============================================================================
-- Host transfer (Track D8)
-- =============================================================================
CREATE TABLE IF NOT EXISTS nimbusware_host_transfer_request (
  transfer_id UUID PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES nimbusware_chat_session(session_id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES nimbusware_project(project_id) ON DELETE CASCADE,
  from_host_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  to_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  initiated_by_user_id UUID NOT NULL REFERENCES nimbusware_user(user_id),
  direction TEXT NOT NULL DEFAULT 'host_nominate_successor'
    CHECK (direction IN ('admin_requests_host', 'host_nominate_successor')),
  promote_to_admin BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN (
      'pending', 'accepted', 'declined', 'expired', 'frozen', 'transferring',
      'completed', 'cancelled'
    )),
  consent_expires_at TIMESTAMPTZ NOT NULL,
  artifact_transfer_expires_at TIMESTAMPTZ NULL,
  from_host_agreed_at TIMESTAMPTZ NULL,
  freeze_started_at TIMESTAMPTZ NULL,
  artifact_manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
  completed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(artifact_manifest) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_nimbusware_host_transfer_session
  ON nimbusware_host_transfer_request (session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS nimbusware_user_optimizer_weights (
  user_id UUID NOT NULL REFERENCES nimbusware_user(user_id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES nimbusware_tenant(tenant_id) ON DELETE CASCADE,
  weights JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, tenant_id),
  CHECK (jsonb_typeof(weights) = 'object')
);

-- =============================================================================
-- run_list_status (GET /v1/runs ?status= read model)
-- =============================================================================
CREATE OR REPLACE VIEW run_list_status AS
SELECT
  run_id,
  CASE
    WHEN has_terminal THEN 'terminal'
    WHEN has_started THEN 'running'
    WHEN last_et = 'run.created' THEN 'created'
    ELSE 'running'
  END AS list_status
FROM (
  SELECT
    run_id,
    BOOL_OR(event_type IN ('run.failed', 'run.completed')) AS has_terminal,
    BOOL_OR(event_type = 'run.started') AS has_started,
    (ARRAY_AGG(event_type ORDER BY store_seq DESC))[1] AS last_et
  FROM event_store
  GROUP BY run_id
) AS agg;
