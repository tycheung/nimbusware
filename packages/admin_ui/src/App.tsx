import { useEffect, useState } from "preact/hooks";
import Router from "preact-router";
import { LoginGate } from "./LoginGate";
import { RunListPage } from "./pages/RunListPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { ConfigPage } from "./pages/ConfigPage";
import { OperatorChatPage } from "./pages/OperatorChatPage";
import { CustomAgentsPage } from "./pages/CustomAgentsPage";
import { StandardsMartPage } from "./pages/StandardsMartPage";
import { PreflightPage } from "./pages/PreflightPage";
import { MetricsPage } from "./pages/MetricsPage";
import { FleetPage } from "./pages/FleetPage";
import { HardwarePage } from "./pages/HardwarePage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { loadBootstrap, type Bootstrap } from "./api/client";

const ADMIN_APP_BASE = "/v1/admin/app";

function adminRouterUrl(): string {
  const path = window.location.pathname;
  if (path === ADMIN_APP_BASE || path === `${ADMIN_APP_BASE}/`) {
    return "/runs";
  }
  if (path.startsWith(`${ADMIN_APP_BASE}/`)) {
    return path.slice(ADMIN_APP_BASE.length) || "/runs";
  }
  return path;
}

export function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);

  useEffect(() => {
    loadBootstrap().then(setBoot);
  }, []);

  if (!boot) {
    return <p class="loading">Loading…</p>;
  }

  const fleetUi = boot.features?.enterprise_fleet_ui === true;

  return (
    <LoginGate
      enterpriseEdition={boot.edition === "enterprise"}
      oidcLoginReady={boot.features?.oidc_login_ready === true}
    >
      <header class="admin-header">
        <h1>Nimbusware Admin</h1>
        <span class="edition">{boot.edition}</span>
      </header>
      <nav class="admin-nav">
        <a href="/v1/admin/app/runs">Runs</a>
        <a href="/v1/admin/app/projects">Projects</a>
        <a href="/v1/admin/app/config">Config</a>
        <a href="/v1/admin/app/chat">Chat</a>
        <a href="/v1/admin/app/agents">Agents</a>
        <a href="/v1/admin/app/standards">Standards</a>
        <a href="/v1/admin/app/preflight">Preflight</a>
        <a href="/v1/admin/app/metrics">Metrics</a>
        <a href="/v1/admin/app/hardware">Hardware</a>
        {fleetUi ? <a href="/v1/admin/app/fleet">Fleet</a> : null}
      </nav>
      <main>
        <Router url={adminRouterUrl()}>
          <RunListPage path="/runs" />
          <RunDetailPage path="/runs/:id" />
          <ProjectsPage path="/projects" />
          <ConfigPage path="/config" />
          <OperatorChatPage path="/chat" />
          <CustomAgentsPage path="/agents" />
          <StandardsMartPage path="/standards" />
          <PreflightPage path="/preflight" />
          <MetricsPage path="/metrics" />
          <HardwarePage path="/hardware" />
          {fleetUi ? <FleetPage path="/fleet" /> : null}
          <RunListPage default />
        </Router>
      </main>
    </LoginGate>
  );
}
