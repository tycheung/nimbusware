# External CI bridge (GitHub Checks)

Maps Hermes **integrator gate** outcomes to GitHub Check Runs so external CI dashboards reflect Nimbusware gate verdicts. Entrypoint: `notify_gate_decision_external` in [`packages/hermes_orchestrator/ci_bridge/external_ci.py`](../../packages/hermes_orchestrator/ci_bridge/external_ci.py).

## When it fires

The bridge runs **best-effort** after the integrator stage emits `gate.decision.emitted` (see [`optional_stages_integrator.py`](../../packages/hermes_orchestrator/_pipeline/optional_stages_integrator.py)). It does **not** post checks for every slice gate or critic verdict — only the integrator gate path wired today.

Other gates remain visible via the Nimbusware timeline and audit export.

## Required configuration

| Variable | Required | Notes |
|----------|----------|--------|
| `GITHUB_TOKEN` | Yes | Personal access token or GitHub App installation token with **`checks:write`** on the target repo |
| `HERMES_CI_GITHUB_REPO` | Yes | Repository slug `owner/name` (e.g. `acme/widget`) |

When either is unset, the bridge returns `{"status": "skipped", "reason": "github_not_configured"}` and the run continues normally.

## Optional configuration

| Variable | Purpose |
|----------|---------|
| `HERMES_CI_HEAD_SHA` | Commit SHA for the check run (default: forty-zero placeholder if unset) |
| `HERMES_TIMELINE_BASE_URL` | Public API base URL prepended to `/v1/runs/{id}/timeline` in check output |

## Check run shape

- **Name:** `hermes/{stage_name}` (stage name from gate payload)
- **Conclusion:** `success` when verdict is `PASS`, otherwise `failure`
- **Output title:** `Hermes gate {stage_name}`
- **Output summary:** `Verdict: {verdict}`

## Operator setup

1. Create a GitHub token with `checks:write` on the repository that should receive status.
2. Export env on the API/worker host (or inject via Kubernetes secret / compose):

```bash
export GITHUB_TOKEN=ghp_...
export HERMES_CI_GITHUB_REPO=your-org/your-repo
export HERMES_CI_HEAD_SHA="${GITHUB_SHA}"   # optional; set in CI-driven runs
export HERMES_TIMELINE_BASE_URL=https://nimbusware.example.com/v1  # optional
```

3. Run a workflow with integrator gate enabled; inspect gate metadata `external_ci` on the timeline event when posting succeeds.

## Security

- Never commit tokens to the repo or Helm values in plain text.
- Use least-privilege tokens scoped to the single repository.
- The bridge catches network/API errors and returns `status: error` without failing the Hermes run.

## GitLab

GitLab pipeline status and MR comments are **not implemented**. Use Nimbusware timeline links or fo400 GitHub Checks only.

## Local verification

```bash
poetry run pytest tests/unit/test_ci_bridge_external.py -q
```
