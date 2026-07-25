import { ComponentChildren } from "preact";
import { useEffect, useState } from "preact/hooks";
import {
  ENTERPRISE_API_KEY_KEY,
  apiBase,
  enterpriseApiKey,
  formatPeelMissMessage,
  formatReadCatchMessage,
  isDomainPeelMiss,
  setEnterpriseApiKey,
} from "./api/client"; // sak500-d

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
  const [oidcMiss, setOidcMiss] = useState("");
  const [consoleRole, setConsoleRole] = useState("admin");

  useEffect(() => {
    if (!oidcLoginReady) return;
    fetch(`${apiBase()}/admin/oauth/session`, { credentials: "include" })
      .then(async (r) => {
        const b = (await r.json()) as {
          authenticated?: boolean;
          console_role?: string;
          via?: string;
          error?: string;
          status?: string;
        };
        if (isDomainPeelMiss(b)) {
          setOidcOk(false);
          setOidcMiss(formatPeelMissMessage(b, "SSO session unavailable"));
          return;
        }
        setOidcMiss("");
        setOidcOk(Boolean(b.authenticated));
        setConsoleRole(String(b.console_role || "admin"));
      })
      .catch((e) => {
        setOidcOk(false);
        setOidcMiss(formatReadCatchMessage(e, "SSO session unavailable"));
      });
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
        {oidcMiss ? <p class="hint">{oidcMiss}</p> : null}
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
          {oidcMiss ? <span class="hint">{oidcMiss}</span> : null}
          {oidcOk ? (
            <span class="muted">
              SSO session active ({consoleRole === "admin" ? "admin" : "read-only"}).
            </span>
          ) : null}
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
