# Deploy pipeline (Phase 6)

Operators wire cloud deploy through Terraform validation, GitHub Actions, and per-user connection labels (no secrets in repo).

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/platform/deploy/terraform-validate` | `fmt` / `validate` / `plan` in workspace; optional `run_id` emits timeline stages |
| GET/PUT | `/v1/platform/deploy/credentials` | Per-user labels: `aws_profile`, `github_repo`, `workflow_path` |
| GET | `/v1/platform/deploy/github-workflow-template` | Copy-ready `.github/workflows/nimbusware-deploy.yml` |

## Storage

- Credential labels: `configs/deploy/users/{user_id}.yaml`
- Workflow template: `configs/deploy/github_actions_nimbusware.yaml`

## Maker UI

- **Progress / Review** deploy cockpit — **Run Terraform validate**, CI status from `terraform.*` / `ci.*` timeline stages
- **Settings → Deploy connections** — sync labels with vault API

Live `terraform apply` and hosted smoke tests require operator secrets (Admin API connections or CI environment).
