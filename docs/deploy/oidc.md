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

## Session and logout

- Session cookie TTL: **3600 seconds** (see `admin_oauth.py`).
- Logout: `POST /v1/admin/oauth/logout` or SSO logout button in Admin header.
- IdP token exchange in production: configure issuer token endpoint separately; v1 validates authorization code + PKCE state only (mock path for CI).

## Group mapping (future)

Map IdP `groups` claim → `maker_admin` vs read-only via env `NIMBUSWARE_OIDC_ADMIN_GROUPS` (not implemented in v1).

## Code

- [`packages/nimbusware_env/oidc_config.py`](../../packages/nimbusware_env/oidc_config.py)
- [`packages/nimbusware_console/services/oauth_pkce.py`](../../packages/nimbusware_console/services/oauth_pkce.py)
- [`packages/nimbusware_api/routes/admin_oauth.py`](../../packages/nimbusware_api/routes/admin_oauth.py)

## Non-goals

- Replacing `nimbusware_iam` API keys for machine clients.
- Embedding IdP tokens in `sessionStorage` for API calls.
