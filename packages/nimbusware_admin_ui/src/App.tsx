import { useEffect, useState } from "preact/hooks";
import Router from "preact-router";
import { LoginGate } from "./LoginGate";
import { RunListPage } from "./pages/RunListPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { ConfigPage } from "./pages/ConfigPage";
import { OperatorChatPage } from "./pages/OperatorChatPage";
import { loadBootstrap, type Bootstrap } from "./api/client";

export function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);

  useEffect(() => {
    loadBootstrap().then(setBoot);
  }, []);

  if (!boot) {
    return <p class="loading">Loading…</p>;
  }

  return (
    <LoginGate>
      <header class="admin-header">
        <h1>Nimbusware Admin</h1>
        <span class="edition">{boot.edition}</span>
      </header>
      <nav class="admin-nav">
        <a href="/v1/admin/app/runs">Runs</a>
        <a href="/v1/admin/app/config">Config</a>
        <a href="/v1/admin/app/chat">Chat</a>
      </nav>
      <main>
        <Router>
          <RunListPage path="/runs" />
          <RunDetailPage path="/runs/:id" />
          <ConfigPage path="/config" />
          <OperatorChatPage path="/chat" />
          <RunListPage default />
        </Router>
      </main>
    </LoginGate>
  );
}
