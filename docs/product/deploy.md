# Deploy pipeline

Operators wire cloud deploy through Terraform validation, GitHub Actions, and per-user connection labels (no secrets in repo).

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/platform/deploy/terraform-validate` | `fmt` / `validate` / `plan` in workspace; optional `run_id` emits timeline stages |
| POST | `/v1/platform/deploy/approve` | Record operator approval (`deploy.approved` on run timeline) |
| POST | `/v1/platform/deploy/apply` | `terraform apply` after approval (or `deploy_hands_off` autopilot profile); plan-only skip when credentials empty; auto-runs HTTP smoke when live URLs are returned |
| POST | `/v1/platform/deploy/smoke` | HTTP checks (and optional Playwright) against `api_url` / `web_url` from apply outputs or request body; requires successful `deploy.apply` |
| POST | `/v1/platform/deploy/rollback` | Guarded `terraform destroy` or restore pre-apply state snapshot (`mode`: `destroy` \| `previous`); requires `deploy.approved` + successful `deploy.apply` |
| GET | `/v1/platform/deploy/environments` | Allowed deploy targets: `dev`, `staging`, `prod` |
| GET/PUT | `/v1/platform/deploy/credentials` | Per-user labels: `aws_profile`, `github_repo`, `workflow_path`, `deploy_environment` |
| GET | `/v1/platform/deploy/github-workflow-template` | Copy-ready `.github/workflows/nimbusware-deploy.yml` |

## Storage

- Credential labels: `configs/deploy/users/{user_id}.yaml`
- Workflow template: `configs/deploy/github_actions_nimbusware.yaml`

## Maker UI

- **Progress / Review** deploy cockpit — **Run Terraform validate**, **Approve deploy**, **Apply deploy**, **Run smoke test**, **Rollback deploy** (destroy or previous state), CI status from timeline stages
- **Settings → Deploy connections** — sync labels with vault API

Autopilot profiles `deploy_guided` (requires manual approval) and `deploy_hands_off` (level ≥ 9, no `stop_before_deploy_apply`) control whether apply may auto-record approval.

Apply, smoke, and rollback pass `TF_VAR_environment` / `NIMBUSWARE_DEPLOY_ENV` to Terraform subprocesses. The cockpit and Settings expose the environment selector; stack manifests may freeze `deploy_environment` at scope confirm.

When `deploy` is in the frozen stack manifest, campaign **completion_eval** requires a successful `deploy.smoke` timeline stage before the run may finalize as PASS.

Live `terraform apply` and hosted smoke tests require operator secrets (Admin API connections or CI environment). Apply without approval returns **403** (`deploy_approval_required`).
