# Enterprise integrator gate runbook

Operator guide for enabling the **bundle integrator gate**, live HTTP adapter probes, and external CI status bridges on **Enterprise** deployments.

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Edition** | `NIMBUSWARE_EDITION=enterprise` |
| **Postgres** | `NIMBUSWARE_DATABASE_URL` — integrator thresholds and bundle catalog can persist in `nimbusware_config_document` |
| **Bundle catalog** | `configs/integrator/thresholds.yaml` or materialized `policy/integrator-thresholds` |
| **Workflow profile** | Profile with `integrator_gate.enabled: true` (or force via env) |

Verify edition: `GET /v1/platform/edition` returns `enterprise`.

## Enable the integrator gate

The integrator stage scores bundle compatibility and emits `gate.decision.emitted` on `bundle_compatibility`. Enable via **any** of:

| Mechanism | Setting |
|-----------|---------|
| Env force | `NIMBUSWARE_EMIT_INTEGRATOR_GATE=on` |
| Thresholds YAML | `configs/integrator/thresholds.yaml` → `enabled: true` |
| Workflow block | `integrator_gate.enabled: true` in the active workflow profile |

Minimum score override (optional):

```yaml
# configs/integrator/thresholds.yaml
enabled: true
min_score_to_pass: 0.65
```

Or per-workflow:

```yaml
integrator_gate:
  enabled: true
  min_score_to_pass: 0.7
  project_tags: [api_bridge, rest]
```

Env override: `NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS=0.7`.

Optional dependency preflight (emits LOW integrator findings before gate):

```bash
export NIMBUSWARE_INTEGRATOR_DEP_PREFLIGHT=on
```

## Live HTTP probe (api_bridge adapters)

When the integration adapter writer targets an `api_bridge` bundle, Nimbusware probes the adapter health endpoint before the integrator gate verdict. Probe tuning:

| Variable | Default | Purpose |
|----------|---------|---------|
| `NIMBUSWARE_INTEGRATOR_PROBE_MAX_ATTEMPTS` | 3 | Retry count |
| `NIMBUSWARE_INTEGRATOR_PROBE_RETRY_DELAY` | 0.25 | Base seconds (exponential backoff) |

Successful probes attach `integrator_live_context.http_probe` on the gate event metadata (`reachable`, `status_code`, `ok`, `body_preview`, `attempts`). Failed probes surface in Admin run detail and block PASS when the adapter is unreachable.

### Verification

1. Start a run with integrator gate enabled and an `api_bridge` bundle selected.
2. Inspect `GET /v1/runs/{id}/timeline` — gate metadata includes `integrator_live_context`.
3. Confirm `http_probe.ok` is true before promoting catalog candidates.

Unit coverage: `tests/unit/test_integrator_live_context.py`, `tests/e2e/journeys/test_tiny_api_fixture_repo.py`.

## External CI bridge

After the integrator gate emits, Nimbusware posts a GitHub Check Run or GitLab commit status (best-effort). Configure per [external-ci-bridge.md](external-ci-bridge.md).

Quick GitHub setup:

```bash
export GITHUB_TOKEN=ghp_...
export NIMBUSWARE_CI_GITHUB_REPO=your-org/your-repo
export NIMBUSWARE_CI_HEAD_SHA="${GITHUB_SHA}"
export NIMBUSWARE_TIMELINE_BASE_URL=https://nimbusware.example.com
```

Gate metadata includes `external_ci` when posting succeeds.

## Enterprise operator workflow

1. **Catalog** — maintain bundle rows in Postgres or `configs/bundles/catalog.yaml`; promote research candidates via `POST /v1/bundles/catalog-candidates/{run_id}/{candidate_id}/promote` ([operator-bundle-catalog-promotion.md](../operator-bundle-catalog-promotion.md)).
2. **Profile** — enable `integrator_gate` on production workflow profiles used for bundle integration runs.
3. **Run** — `POST /v1/runs` with `workflow_profile` that includes integrator gate; or Maker **Build** with bundle integrator stage.
4. **Review** — Admin run detail: integrator score, compatibility ranking, live probe, external CI link.
5. **Remediate** — on FAIL, inspect `integrator_below_threshold` or probe failures; adjust bundle tags, adapter manifest, or thresholds.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| No integrator gate event | `NIMBUSWARE_EMIT_INTEGRATOR_GATE` not `on` and thresholds/workflow disabled |
| Gate skipped (no thresholds file) | Create `configs/integrator/thresholds.yaml` or enable Postgres materializer |
| Probe always fails | Adapter URL, TLS, firewall; increase `NIMBUSWARE_INTEGRATOR_PROBE_MAX_ATTEMPTS` |
| External CI `skipped` | Missing `GITHUB_TOKEN` / `NIMBUSWARE_GITLAB_TOKEN` pair |
| Score below threshold | Review `bundle_compatibility_ranking` in gate metadata; adjust `project_tags` |

## Security

- Store CI tokens in a secret manager; never commit to Helm values or `.env` in git.
- Scope tokens to a single repository/project.
- The external CI bridge catches API errors and does not fail the Nimbusware run.

## Related

- [external-ci-bridge.md](external-ci-bridge.md) — GitHub/GitLab status mapping
- [operator-bundle-catalog-promotion.md](../operator-bundle-catalog-promotion.md) — catalog candidate flow
- [enterprise-buyer.md](../enterprise-buyer.md) — buyer checklist
