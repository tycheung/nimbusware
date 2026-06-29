# Deploy pipeline

Operators wire cloud deploy through Terraform validation, GitHub Actions, and per-user connection labels (no secrets in repo).

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/platform/deploy/audit` | List deploy audit rows for optional `run_id` (hashed user refs; no secrets) |
| POST | `/v1/platform/deploy/terraform-validate` | `fmt` / `validate` / `plan` in workspace; optional `run_id` emits timeline stages |
| POST | `/v1/platform/deploy/approve` | Record operator approval (`deploy.approved` on run timeline) |
| POST | `/v1/platform/deploy/apply` | `terraform apply` after approval (or `deploy_hands_off` autopilot profile); plan-only skip when credentials empty; auto-runs HTTP smoke when live URLs are returned |
| POST | `/v1/platform/deploy/smoke` | HTTP checks (and optional Playwright) against `api_url` / `web_url` from apply outputs or request body; requires successful `deploy.apply` |
| POST | `/v1/platform/deploy/rollback` | Guarded `terraform destroy` or restore pre-apply state snapshot (`mode`: `destroy` \| `previous`); requires `deploy.approved` + successful `deploy.apply` |
| GET | `/v1/platform/deploy/environments` | Allowed deploy targets: `dev`, `staging`, `prod` |
| GET/PUT | `/v1/platform/deploy/credentials` | Per-user labels: `aws_profile`, `github_repo`, `workflow_path`, `deploy_environment` |
| POST | `/v1/platform/deploy/ci-poll` | Poll latest GitHub Actions run via `gh` CLI; emits `ci.workflow` timeline stages when configured |
| GET | `/v1/platform/deploy/github-workflow-template` | Copy-ready `.github/workflows/nimbusware-deploy.yml` |

## Enterprise fleet policy

| Method | Path | Purpose |
|--------|------|---------|
| GET/PUT | `/v1/enterprise/audit-policy` | Tenant legal hold + redaction patterns (Admin Fleet toggle; blocks event-store purge) |
| GET/PUT | `/v1/enterprise/tenants/{ref}/deploy-policy` | Tenant allowlist for deploy targets (`aws-ecs`, `aws-static-site`, `github-actions`) |
| GET/PUT | `/v1/enterprise/tenants/{ref}/deploy-approval-policy` | Approval chain: `maker_only`, `session_admin`, or `dual_control` (maker + fleet admin) |

Apply and credential save enforce the tenant allowlist when `NIMBUSWARE_SETUP_BUNDLE=enterprise`. **Dual-control** tenants require two timeline approvals (maker, then fleet admin with `maker_admin` scope) before apply; partial approval returns `status: partial` from the approve API. Credential updates and deploy apply/rollback append hashed audit rows to `.nimbusware/platform/deploy_audit.jsonl` (no secret material).

## Storage

- Credential labels: `configs/deploy/users/{user_id}.yaml`
- Fleet deploy allowlist: `configs/enterprise/fleet_deploy_policies.yaml`
- Fleet deploy approval chain: `configs/enterprise/fleet_deploy_approval_policies.yaml`
- Fleet slice caps: `configs/enterprise/fleet_slice_policies.yaml` (clamps slice budgets for enterprise tenants)
- Workflow template: `configs/deploy/github_actions_nimbusware.yaml`

## Maker UI

- **Progress / Review** deploy cockpit — **Run Terraform validate**, **Approve deploy**, **Apply deploy**, **Run smoke test**, **Rollback deploy** (destroy or previous state), CI status from timeline stages; refresh polls GitHub Actions when `github_repo` is configured
- **Review deploy audit** — timeline of credential updates and apply/rollback actions for the active run (hashed user refs)
- **Settings → Deploy connections** — sync labels with vault API

Autopilot profiles `deploy_guided` (requires manual approval) and `deploy_hands_off` (level ≥ 9, no `stop_before_deploy_apply`) control whether apply may auto-record approval.

Apply, smoke, and rollback pass `TF_VAR_environment` / `NIMBUSWARE_DEPLOY_ENV` to Terraform subprocesses. The cockpit and Settings expose the environment selector; stack manifests may freeze `deploy_environment` at scope confirm.

When `deploy` is in the frozen stack manifest, campaign **completion_eval** requires a successful `deploy.smoke` timeline stage before the run may finalize as PASS.

## Agent roles

Full-stack campaigns with a `deploy` surface register **`infra_writer`** in `configs/roles.yaml` and map it via `stack_catalog.writer_role_for_surface("deploy")`. Binding preflight (`binding_preflight.py`) includes `infra_writer` in `roles` and `surface_stage_map` when the manifest lists `deploy`. Collab **`@devops`** routes to both `integration_adapter_writer` and `infra_writer` (`configs/collab/disciplines.yaml`). Critique pairings pair `infra_writer` with product, domain, and security critics.

Live `terraform apply` and hosted smoke tests require operator secrets (Admin API connections or CI environment). Apply without sufficient approval returns **403** (`deploy_approval_required` or `deploy_dual_control_pending`).
