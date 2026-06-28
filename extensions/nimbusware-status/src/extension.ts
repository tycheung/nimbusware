import * as vscode from "vscode";

import { deployLinksFromTimeline } from "./deploy_links";
import { disciplineRoutes } from "./discipline_routes";
import { fetchScopeRecommend, showScopeCard } from "./scope_card";

let pollTimer: ReturnType<typeof setInterval> | undefined;

function apiBase(): string {
  return String(vscode.workspace.getConfiguration("nimbusware").get<string>("apiBase") || "http://127.0.0.1:8765/v1");
}

function activeRunId(): string {
  return String(vscode.workspace.getConfiguration("nimbusware").get<string>("activeRunId") || "").trim();
}

function soloHat(): string {
  return String(vscode.workspace.getConfiguration("nimbusware").get<string>("soloDiscipline") || "").trim();
}

async function fetchRunStatus(apiBaseUrl: string, runId: string): Promise<string> {
  const url = `${apiBaseUrl.replace(/\/$/, "")}/runs/${runId}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    return `run ${runId.slice(0, 8)}… (HTTP ${resp.status})`;
  }
  const body = (await resp.json()) as { status?: string; gate_summary?: string };
  const status = String(body.status || "unknown");
  const gate = body.gate_summary ? ` · ${body.gate_summary}` : "";
  return `Nimbusware ${runId.slice(0, 8)}… ${status}${gate}`;
}

async function fetchRunTimeline(apiBaseUrl: string, runId: string): Promise<unknown[]> {
  const url = `${apiBaseUrl.replace(/\/$/, "")}/runs/${runId}/timeline`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`timeline HTTP ${resp.status}`);
  }
  const body = (await resp.json()) as { events?: unknown[] };
  return body.events || [];
}

async function promptTextFromEditor(): Promise<string | undefined> {
  const editor = vscode.window.activeTextEditor;
  const selected = editor?.document.getText(editor.selection).trim();
  if (selected) {
    return selected;
  }
  const input = await vscode.window.showInputBox({
    prompt: "Enter a business prompt or message with @discipline mentions",
    placeHolder: "Build a todo app with API and web UI",
  });
  return input?.trim() || undefined;
}

export function activate(context: vscode.ExtensionContext): void {
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
  item.command = "nimbusware.openMakerProgress";
  context.subscriptions.push(item);

  const refresh = async () => {
    const runId = activeRunId();
    const base = apiBase();
    if (!runId) {
      item.hide();
      return;
    }
    try {
      item.text = await fetchRunStatus(base, runId);
      item.tooltip = "Open Maker Progress (click)";
      item.show();
    } catch {
      item.text = `Nimbusware ${runId.slice(0, 8)}… offline`;
      item.show();
    }
  };

  context.subscriptions.push(
    vscode.commands.registerCommand("nimbusware.openMakerProgress", () => {
      const runId = activeRunId();
      const base = apiBase().replace(/\/v1$/, "");
      const url = runId ? `${base}/v1/maker/app/#/progress?run_id=${runId}` : `${base}/v1/maker/app/`;
      vscode.env.openExternal(vscode.Uri.parse(url));
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nimbusware.showScopeCard", async () => {
      const text = await promptTextFromEditor();
      if (!text) {
        return;
      }
      try {
        const scope = await fetchScopeRecommend(apiBase(), text);
        await showScopeCard(scope);
      } catch (err) {
        void vscode.window.showErrorMessage(`Scope card failed: ${String(err)}`);
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nimbusware.previewDisciplineRoutes", async () => {
      const text = await promptTextFromEditor();
      if (!text) {
        return;
      }
      const routes = disciplineRoutes(text, soloHat() || undefined);
      if (!routes.length) {
        void vscode.window.showInformationMessage("No @discipline mentions and no solo hat configured.");
        return;
      }
      const lines = routes.map((r) => `${r.discipline} → ${r.taxonomy_key} (${r.source})`);
      const pick = await vscode.window.showQuickPick(lines, {
        title: "Discipline routes (parity with Maker @ routing)",
        canPickMany: true,
      });
      if (pick?.length) {
        void vscode.window.showInformationMessage(pick.join("; "));
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nimbusware.openDeployLinks", async () => {
      const runId = activeRunId();
      if (!runId) {
        void vscode.window.showWarningMessage("Set nimbusware.activeRunId to open deploy links.");
        return;
      }
      try {
        const events = await fetchRunTimeline(apiBase(), runId);
        const links = deployLinksFromTimeline(events);
        const choices: string[] = [];
        if (links.apiUrl) choices.push(`API: ${links.apiUrl}`);
        if (links.webUrl) choices.push(`Web: ${links.webUrl}`);
        choices.push(`Open Maker deploy cockpit`);
        const picked = await vscode.window.showQuickPick(choices, {
          title: `Deploy (${links.ciStatus}) — ${links.ciDetail}`,
        });
        if (!picked) {
          return;
        }
        if (picked.startsWith("API:")) {
          vscode.env.openExternal(vscode.Uri.parse(links.apiUrl));
        } else if (picked.startsWith("Web:")) {
          vscode.env.openExternal(vscode.Uri.parse(links.webUrl));
        } else {
          const base = apiBase().replace(/\/v1$/, "");
          vscode.env.openExternal(vscode.Uri.parse(`${base}/v1/maker/app/#/progress?run_id=${runId}`));
        }
      } catch (err) {
        void vscode.window.showErrorMessage(`Deploy links failed: ${String(err)}`);
      }
    }),
  );

  void refresh();
  pollTimer = setInterval(() => void refresh(), 15000);
  context.subscriptions.push({ dispose: () => clearInterval(pollTimer) });

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("nimbusware")) {
        void refresh();
      }
    }),
  );
}

export function deactivate(): void {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
}
