import { ComponentChildren } from "preact";
import { useState } from "preact/hooks";

const TOKEN_KEY = "nimbusware_admin_token";

export function LoginGate({ children }: { children: ComponentChildren }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");

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
        <button
          type="button"
          onClick={() => {
            sessionStorage.setItem(TOKEN_KEY, token.trim());
            setToken(token.trim());
          }}
        >
          Unlock
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
