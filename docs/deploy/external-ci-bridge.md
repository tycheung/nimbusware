# External CI bridge (GitHub Checks / GitLab)

Maps Nimbusware gate outcomes to GitHub Check Runs or GitLab commit statuses so external CI dashboards reflect Nimbusware gate verdicts. Entrypoint: `notify_gate_decision_external` / `attach_external_ci_metadata` in [`packages/nimbusware_orchestrator/ci_bridge/external_ci.py`](../../packages/nimbusware_orchestrator/ci_bridge/external_ci.py).

## When it fires

The bridge runs **best-effort** (never raises) after these stages emit:

| Stage | Emitter |
|-------|---------|
| `bundle_compatibility` (integrator) | [`optional_stages_integrator.py`](../../packages/nimbusware_orchestrator/_pipeline/optional_stages_integrator.py) |
| `slice.gate` | [`_pipeline/micro_slice.py`](../../packages/nimbusware_orchestrator/_pipeline/micro_slice.py) `record_micro_slice_gate` |
| `factory.gate` | [`factory_cadence.py`](../../packages/nimbusware_orchestrator/factory_cadence.py) maintenance cadence pass |

Successful posts attach `metadata.external_ci` on the stage event. Other gates remain visible via the Nimbusware timeline and audit export.

## Provider selection

GitHub is tried first when `GITHUB_TOKEN` and `NIMBUSWARE_CI_GITHUB_REPO` are set. Otherwise GitLab is used when `NIMBUSWARE_GITLAB_TOKEN` (or `GITLAB_TOKEN`) and `NIMBUSWARE_CI_GITLAB_PROJECT` are set. When neither provider is configured, the bridge returns `{"status": "skipped", "reason": "external_ci_not_configured"}`.

## GitHub configuration

| Variable | Required | Notes |
|----------|----------|--------|
| `GITHUB_TOKEN` | Yes | Token with **`checks:write`** on the target repo |
| `NIMBUSWARE_CI_GITHUB_REPO` | Yes | Repository slug `owner/name` (e.g. `acme/widget`) |

Check run shape:

- **Name:** `nimbusware/{stage_name}`
- **Conclusion:** `success` when verdict is `PASS`, otherwise `failure`

## GitLab configuration

| Variable | Required | Notes |
|----------|----------|--------|
| `NIMBUSWARE_GITLAB_TOKEN` or `GITLAB_TOKEN` | Yes | Personal/project access token with **`api`** scope |
| `NIMBUSWARE_CI_GITLAB_PROJECT` | Yes | Numeric project id or `namespace/project` path |
| `NIMBUSWARE_CI_HEAD_SHA` | Yes | Commit SHA for the pipeline status |
| `NIMBUSWARE_GITLAB_API_BASE` | No | Default `https://gitlab.com/api/v4` (self-managed: `https://gitlab.example.com/api/v4`) |

Commit status shape:

- **Name:** `nimbusware/{stage_name}`
- **State:** `success` when verdict is `PASS`, otherwise `failed`
- **target_url:** timeline link when `NIMBUSWARE_TIMELINE_BASE_URL` is set

## Optional (both providers)

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_CI_HEAD_SHA` | Commit SHA (GitHub default: forty-zero placeholder if unset) |
| `NIMBUSWARE_TIMELINE_BASE_URL` | Public API base prepended to `/v1/runs/{id}/timeline` in output |

## Operator setup (GitHub)

```bash
export GITHUB_TOKEN=ghp_...
export NIMBUSWARE_CI_GITHUB_REPO=your-org/your-repo
export NIMBUSWARE_CI_HEAD_SHA="${GITHUB_SHA}"
export NIMBUSWARE_TIMELINE_BASE_URL=https://nimbusware.example.com/v1
```

## Operator setup (GitLab)

```bash
export NIMBUSWARE_GITLAB_TOKEN=glpat-...
export NIMBUSWARE_CI_GITLAB_PROJECT=your-group/your-project
export NIMBUSWARE_CI_HEAD_SHA="${CI_COMMIT_SHA}"
export NIMBUSWARE_TIMELINE_BASE_URL=https://nimbusware.example.com/v1
```

Run a workflow with integrator gate enabled; inspect gate metadata `external_ci` on the timeline event when posting succeeds.

## Security

- Never commit tokens to the repo or Helm values in plain text.
- Use least-privilege tokens scoped to the single project.
- The bridge catches network/API errors and returns `status: error` without failing the Nimbusware run.

## Local verification

```bash
poetry run pytest tests/unit/test_ci_bridge_external.py -q
```
