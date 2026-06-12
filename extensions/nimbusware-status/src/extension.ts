import * as vscode from "vscode";

let pollTimer: ReturnType<typeof setInterval> | undefined;

async function fetchRunStatus(apiBase: string, runId: string): Promise<string> {
  const url = `${apiBase.replace(/\/$/, "")}/runs/${runId}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    return `run ${runId.slice(0, 8)}… (HTTP ${resp.status})`;
  }
  const body = (await resp.json()) as { status?: string; gate_summary?: string };
  const status = String(body.status || "unknown");
  const gate = body.gate_summary ? ` · ${body.gate_summary}` : "";
  return `Nimbusware ${runId.slice(0, 8)}… ${status}${gate}`;
}

export function activate(context: vscode.ExtensionContext): void {
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
  item.command = "nimbusware.openMakerProgress";
  context.subscriptions.push(item);

  const refresh = async () => {
    const cfg = vscode.workspace.getConfiguration("nimbusware");
    const runId = String(cfg.get<string>("activeRunId") || "").trim();
    const apiBase = String(cfg.get<string>("apiBase") || "http://127.0.0.1:8765/v1");
    if (!runId) {
      item.hide();
      return;
    }
    try {
      item.text = await fetchRunStatus(apiBase, runId);
      item.tooltip = "Open Maker Progress";
      item.show();
    } catch {
      item.text = `Nimbusware ${runId.slice(0, 8)}… offline`;
      item.show();
    }
  };

  context.subscriptions.push(
    vscode.commands.registerCommand("nimbusware.openMakerProgress", () => {
      const cfg = vscode.workspace.getConfiguration("nimbusware");
      const runId = String(cfg.get<string>("activeRunId") || "").trim();
      const base = String(cfg.get("apiBase") || "http://127.0.0.1:8765/v1").replace(/\/v1$/, "");
      const url = runId ? `${base}/v1/maker/app/#/progress?run_id=${runId}` : `${base}/v1/maker/app/`;
      vscode.env.openExternal(vscode.Uri.parse(url));
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
