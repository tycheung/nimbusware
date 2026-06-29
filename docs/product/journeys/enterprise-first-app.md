# Enterprise AI — first full-stack app

Build a governed full-stack app under tenant fleet policy: mandatory discovery fields, deploy approval chain, regulated stack allowlist, collab guest policy, and compliance widgets in Maker Home.

## Prerequisites

1. Install with `--setup-bundle enterprise` ([install-profiles.md](../../install-profiles.md)).
2. Bootstrap IAM: `POST /v1/enterprise/iam/bootstrap` with admin token.
3. Configure fleet policies in **Admin → Fleet** (or YAML seeds under `configs/enterprise/`).

## Fleet policies to review first

| Policy | API | Admin Fleet panel |
|--------|-----|-------------------|
| Discovery required fields | `GET/PUT .../discovery-policy` | Discovery policy |
| Deploy approval chain | `GET/PUT .../deploy-approval-policy` | Deploy approval |
| Allowed deploy targets | `GET/PUT .../deploy-policy` | Deploy targets |
| Regulated stack allowlist | `GET/PUT .../stack-policy` | Stack policy |
| External collab guests | `GET/PUT .../collab-policy` | Collab guest policy |
| Legal hold | audit policy API | Legal hold toggle |

Details: [enterprise-buyer.md](../../enterprise-buyer.md), [product/admin.md](../admin.md).

## Journey steps

### 1. Check governance (Home)

Maker Home loads `GET /v1/platform/fleet-governance` and `GET /v1/enterprise/compliance/summary`:

- Mandatory discovery fields (hosting, data residency, etc.)
- Deploy approval chain (`maker_only`, `session_admin`, `dual_control`)
- Allowed deploy targets and enforcement depth clamps

### 2. Discovery under policy (Chat)

1. Start a **campaign** for *Build a todo app with web UI and API*.
2. Complete all **mandatory** discovery fields — Start is blocked until satisfied.
3. Stack recommendations clamp to tenant **stack-policy** allowlist (e.g. `api: fastapi_python`, `web: react_vite`).
4. **Approve manifest** before campaign start.

### 3. Deploy with approval (Progress / Review)

When the manifest includes **deploy**:

1. **Run Terraform validate** in the deploy cockpit.
2. **Approve deploy** — records approver per tenant deploy-approval policy.
3. **Apply deploy** after approval; credential refs hash into `.nimbusware/platform/deploy_audit.jsonl`.
4. **Run smoke test** — required before `completion_eval` may PASS.
5. Review **deploy audit timeline** in Review (`GET /v1/platform/deploy/audit?run_id=`).

### 4. Collab with guest policy (optional)

- External invite-link guests require `allow_external_collaborators` on tenant collab policy (enterprise bundle).
- Admin Fleet toggles the policy; join API enforces capacity and guest rules.

### 5. Compliance export

- Per-run: `GET /v1/runs/{id}/audit-export`
- Fleet: `GET /v1/enterprise/audit-export`

## What differs from default bundle

| Control | Enterprise |
|---------|------------|
| Setup bundle | `enterprise` — strict env at install |
| Discovery | Mandatory fields before full-stack start |
| Stacks | Recommendations clamped to fleet allowlist |
| Deploy | Approval chain + target allowlist + audit jsonl |
| Collab guests | Tenant policy gate on external link joins |

## Next steps

- [enterprise-buyer.md](../../enterprise-buyer.md) — security checklist
- [deploy.md](../deploy.md) — apply gate and rollback
- [engineer-first-app.md](engineer-first-app.md) — solo hat and collab disciplines (same Chat UX when collab enabled)
