import { ComponentChildren } from "preact";
import { useState } from "preact/hooks";
import {
  ENTERPRISE_API_KEY_KEY,
  enterpriseApiKey,
  setEnterpriseApiKey,
} from "./api/client";

const TOKEN_KEY = "nimbusware_admin_token";

export function LoginGate({
  children,
  enterpriseEdition = false,
}: {
  children: ComponentChildren;
  enterpriseEdition?: boolean;
}) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem(ENTERPRISE_API_KEY_KEY) || "");

  if (!token) {
    return (
      <div class="login-panel">
        <h2>Admin sign-in</h2>
        <p>Enter your NIMBUSWARE_ADMIN_TOKEN.</p>
        <input
          type="password"
          value={token}
          onInput={(e) => setToken((e.target as HTMLInputElement).value)}
          placeholder="Admin token"
        />
        {enterpriseEdition ? (
          <>
            <p>Enterprise: optional API key for fleet panels (or set later).</p>
            <input
              type="password"
              value={apiKey}
              onInput={(e) => setApiKey((e.target as HTMLInputElement).value)}
              placeholder="X-Nimbusware-Api-Key"
            />
          </>
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
          <label>
            Enterprise API key{" "}
            <input
              type="password"
              value={apiKey}
              onInput={(e) => setApiKey((e.target as HTMLInputElement).value)}
              placeholder={enterpriseApiKey() ? "••••••••" : "Required for Fleet tab"}
            />
          </label>
          <button
            type="button"
            class="secondary"
            onClick={() => setEnterpriseApiKey(apiKey)}
          >
            Save key
          </button>
        </div>
      ) : null}
      {children}
    </>
  );
}
