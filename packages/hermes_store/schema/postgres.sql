-- Hermes PostgreSQL bootstrap (greenfield, single file).
-- Apply to an empty database: psql "$HERMES_DATABASE_URL" -v ON_ERROR_STOP=1 -f postgres.sql
-- Lockstep with agent_core.models.EventType (see hermes_store.allowed_types.allowed_event_type_values).

-- =============================================================================
-- event_store (append-only, plan §19.2)
-- =============================================================================
CREATE TABLE IF NOT EXISTS event_store (
  store_seq BIGSERIAL NOT NULL,
  event_id UUID PRIMARY KEY,
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
    'self_refinement.loop.signalled'
  ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_store_store_seq ON event_store(store_seq);
CREATE INDEX IF NOT EXISTS idx_event_store_run_seq ON event_store(run_id, store_seq);

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
-- hermes_roles_registry (optional DB-backed role registry, plan §5)
-- =============================================================================
CREATE TABLE IF NOT EXISTS hermes_roles_registry (
  taxonomy_key TEXT PRIMARY KEY,
  role_id UUID NOT NULL,
  display_name TEXT NOT NULL DEFAULT ''
);

INSERT INTO hermes_roles_registry (taxonomy_key, role_id, display_name) VALUES
  ('planner', '11111111-1111-4111-8111-111111111101'::uuid, 'Planner'),
  ('product_reference_critic', '22222222-2222-4222-8222-222222222202'::uuid, 'Product Reference Critic'),
  ('domain_critic', '33333333-3333-4333-8333-333333333303'::uuid, 'Domain Critic'),
  ('backend_writer', '44444444-4444-4444-8444-444444444404'::uuid, 'Backend Writer'),
  ('test_writer', '55555555-5555-4555-8555-555555555505'::uuid, 'Test Writer')
ON CONFLICT (taxonomy_key) DO NOTHING;

-- =============================================================================
-- hermes_config_document (operator config authority, plan §19.5)
-- =============================================================================
CREATE TABLE IF NOT EXISTS hermes_config_document (
  namespace TEXT NOT NULL,
  document_key TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  content JSONB NOT NULL,
  content_sha256_16 TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (jsonb_typeof(content) = 'object'),
  PRIMARY KEY (namespace, document_key)
);

CREATE INDEX IF NOT EXISTS idx_hermes_config_document_ns
  ON hermes_config_document (namespace);

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
