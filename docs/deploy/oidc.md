# OIDC for Admin Console (Lane V5 design)

## Scope

Enterprise operators may use SSO for the **Admin Console** web app at `/v1/admin/app/`. The Nimbusware **API** continues to authenticate via:

- Individual: open user routes on loopback; `X-Nimbusware-Admin-Token` for admin routes.
- Enterprise: `X-Nimbusware-Api-Key` with `maker_user` / `maker_admin` scopes.

OIDC unlocks the Admin **shell** (httpOnly session cookie). **API calls still require** `X-Nimbusware-Admin-Token` and, for Fleet, `X-Nimbusware-Api-Key`.

## Flow

1. Operator clicks **Sign in with SSO** → `GET /v1/admin/oauth/login` (PKCE + redirect to IdP).
2. IdP callback → `GET /v1/admin/oauth/callback` validates state/code.
3. API sets `nimbusware_oidc_session` cookie (1 hour TTL, signed with admin token secret).
4. Admin SPA checks `GET /v1/admin/oauth/session`; operator enters admin token for `/v1` API calls.

## Environment

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_OIDC_ENABLED` | `1` to enable |
| `NIMBUSWARE_OIDC_ISSUER` | IdP base URL (https) |
| `NIMBUSWARE_OIDC_CLIENT_ID` | OAuth client id |
| `NIMBUSWARE_OIDC_CLIENT_SECRET` | Optional (confidential clients) |
| `NIMBUSWARE_OIDC_REDIRECT_URI` | Callback, e.g. `https://host/v1/admin/oauth/callback` |
| `NIMBUSWARE_OIDC_MOCK` | `1` for dev/CI mock IdP (`/v1/admin/oauth/mock-authorize`) |

## Routes

| Method | Path | Notes |
|--------|------|-------|
| GET | `/v1/admin/oauth/login` | Start login (Enterprise only) |
| GET | `/v1/admin/oauth/callback` | OAuth redirect target |
| GET | `/v1/admin/oauth/session` | `{ "authenticated": true/false }` |
| POST | `/v1/admin/oauth/logout` | Clear session cookie |

## IdP matrix (operator reference)

| IdP | Issuer pattern | Redirect URI | Client type | Scopes |
|-----|----------------|--------------|-------------|--------|
| **Okta** | `https://{org}.okta.com/oauth2/default` | `https://{host}/v1/admin/oauth/callback` | Confidential (secret) | `openid profile email` |
| **Azure AD** | `https://login.microsoftonline.com/{tenant}/v2.0` | Same | Confidential | `openid profile email` |
| **Google Workspace** | `https://accounts.google.com` | Same | Confidential or public + PKCE | `openid email` |
| **Keycloak** | `https://{host}/realms/{realm}` | Same | Confidential | `openid profile email` |

Register the redirect URI exactly as `NIMBUSWARE_OIDC_REDIRECT_URI`. Use HTTPS in production. PKCE (S256) is always used for the authorization request.

## Session and logout

- Session cookie TTL: **3600 seconds** (see `admin_oauth.py`).
- Logout: `POST /v1/admin/oauth/logout` or SSO logout button in Admin header.
- IdP token exchange in production: configure issuer token endpoint separately; v1 validates authorization code + PKCE state only (mock path for CI).

### Session edge cases

| Case | Behavior |
|------|----------|
| PKCE cookie missing on callback | `400` `oidc_pkce_missing` — restart login |
| OAuth `state` mismatch | `401` `oidc_callback_failed` |
| Session `exp` past TTL | `GET /session` → `{ "authenticated": false }` |
| Tampered session HMAC | Treated as unauthenticated |
| Logout | Clears `nimbusware_oidc_session`; API still needs admin token |
| SSO without admin token | Shell unlocks only; `/v1` API calls fail until token entered |

## Rotation runbook

### Client secret rotation (confidential clients)

1. Create a new client secret in the IdP (keep old secret valid during overlap).
2. Update `NIMBUSWARE_OIDC_CLIENT_SECRET` in the deployment secret store.
3. Rolling restart API pods / reload env (no cookie impact).
4. Revoke the old IdP secret after all instances use the new value.

### Admin token rotation (`NIMBUSWARE_ADMIN_TOKEN`)

Session cookies are **HMAC-signed with the admin token secret**. Rotating the admin token **invalidates all existing OIDC session cookies** immediately.

1. Announce maintenance window (operators re-login + re-enter admin token).
2. Set new `NIMBUSWARE_ADMIN_TOKEN` on API and Admin bootstrap.
3. Operators: SSO login again if needed, then paste new admin token in LoginGate.
4. Verify `GET /v1/admin/oauth/session` and a sample `/v1` admin API call.

### Zero-downtime tips

- Rotate IdP client secret before admin token when possible.
- Keep `NIMBUSWARE_OIDC_MOCK=0` in production; use mock only in CI (`oidc_smoke.yml`).

## Mock smoke checklist (CI / dev)

1. `NIMBUSWARE_EDITION=enterprise`, `NIMBUSWARE_OIDC_ENABLED=1`, `NIMBUSWARE_OIDC_MOCK=1`.
2. `GET /v1/admin/oauth/login` → mock authorize → callback → `session.authenticated=true`.
3. `POST /v1/admin/oauth/logout` → `session.authenticated=false`.
4. API route with only SSO (no admin token) must still return `401` for protected admin APIs.

Automated: `.github/workflows/oidc_smoke.yml` runs `tests/api_http/test_admin_oauth.py`.

## Group mapping

Set comma-separated IdP group names that grant **admin** console access (all other SSO users get **readonly** shell):

```env
NIMBUSWARE_OIDC_ADMIN_GROUPS=nimbusware-admins,platform-ops
```

Mock flow: `NIMBUSWARE_OIDC_MOCK_GROUPS` (default `nimbusware-admins`) feeds group resolution on callback.

`GET /v1/admin/oauth/session` returns `{ authenticated, console_role }` where `console_role` is `admin` or `readonly`. API mutations still require `X-Nimbusware-Admin-Token` unless your deployment maps groups to tokens separately.

## Code

- [`packages/env/oidc_config.py`](../../packages/env/oidc_config.py)
- [`packages/console/services/oauth_pkce.py`](../../packages/console/services/oauth_pkce.py)
- [`packages/api/routes/admin_oauth.py`](../../packages/api/routes/admin_oauth.py)

## Non-goals

- Replacing `iam` API keys for machine clients.
- Embedding IdP tokens in `sessionStorage` for API calls.
