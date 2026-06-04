import { ComponentChildren } from "preact";
import { useEffect, useState } from "preact/hooks";
import {
  ENTERPRISE_API_KEY_KEY,
  apiBase,
  enterpriseApiKey,
  setEnterpriseApiKey,
} from "./api/client";

const TOKEN_KEY = "nimbusware_admin_token";

export function LoginGate({
  children,
  enterpriseEdition = false,
  oidcLoginReady = false,
}: {
  children: ComponentChildren;
  enterpriseEdition?: boolean;
  oidcLoginReady?: boolean;
}) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem(ENTERPRISE_API_KEY_KEY) || "");
  const [oidcOk, setOidcOk] = useState(false);

  useEffect(() => {
    if (!oidcLoginReady) return;
    fetch(`${apiBase()}/admin/oauth/session`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : { authenticated: false }))
      .then((b: { authenticated?: boolean }) => setOidcOk(Boolean(b.authenticated)))
      .catch(() => setOidcOk(false));
  }, [oidcLoginReady]);

  const unlocked = Boolean(token.trim()) || oidcOk;

  if (!unlocked) {
    return (
      <div class="login-panel">
        <h2>Admin sign-in</h2>
        <p>Enter your NIMBUSWARE_ADMIN_TOKEN for API access.</p>
        {enterpriseEdition ? (
          <p class="muted">
            Enterprise Fleet tab also needs <code>X-Nimbusware-Api-Key</code> (optional below).
          </p>
        ) : null}
        <input
          type="password"
          value={token}
          onInput={(e) => setToken((e.target as HTMLInputElement).value)}
          placeholder="Admin token"
        />
        {enterpriseEdition ? (
          <>
            <input
              type="password"
              value={apiKey}
              onInput={(e) => setApiKey((e.target as HTMLInputElement).value)}
              placeholder="Enterprise API key (optional)"
            />
          </>
        ) : null}
        {oidcLoginReady ? (
          <p>
            <a class="button-link" href={`${apiBase()}/admin/oauth/login`}>
              Sign in with SSO
            </a>
          </p>
        ) : null}
        <button
          type="button"
          onClick={() => {
            sessionStorage.setItem(TOKEN_KEY, token.trim());
            setToken(token.trim());
            if (enterpriseEdition) {
              setEnterpriseApiKey(apiKey);
            }
          }}
        >
          Unlock
        </button>
      </div>
    );
  }

  return (
    <>
      {enterpriseEdition ? (
        <div class="enterprise-key-bar">
          {oidcOk ? <span class="muted">SSO session active.</span> : null}
          <label>
            Enterprise API key{" "}
            <input
              type="password"
              value={apiKey}
              onInput={(e) => setApiKey((e.target as HTMLInputElement).value)}
              placeholder={enterpriseApiKey() ? "••••••••" : "Required for Fleet tab"}
            />
          </label>
          <button type="button" class="secondary" onClick={() => setEnterpriseApiKey(apiKey)}>
            Save key
          </button>
          {oidcLoginReady ? (
            <button
              type="button"
              class="secondary"
              onClick={() => {
                void fetch(`${apiBase()}/admin/oauth/logout`, {
                  method: "POST",
                  credentials: "include",
                }).then(() => setOidcOk(false));
              }}
            >
              SSO logout
            </button>
          ) : null}
        </div>
      ) : null}
      {!token.trim() && oidcOk ? (
        <p class="muted enterprise-key-bar">
          Add an admin token above for API calls (SSO unlocks the shell only).
        </p>
      ) : null}
      {children}
    </>
  );
}
