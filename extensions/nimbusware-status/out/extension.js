"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
let pollTimer;
async function fetchRunStatus(apiBase, runId) {
    const url = `${apiBase.replace(/\/$/, "")}/runs/${runId}`;
    const resp = await fetch(url);
    if (!resp.ok) {
        return `run ${runId.slice(0, 8)}… (HTTP ${resp.status})`;
    }
    const body = (await resp.json());
    const status = String(body.status || "unknown");
    const gate = body.gate_summary ? ` · ${body.gate_summary}` : "";
    return `Nimbusware ${runId.slice(0, 8)}… ${status}${gate}`;
}
function activate(context) {
    const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
    item.command = "nimbusware.openMakerProgress";
    context.subscriptions.push(item);
    const refresh = async () => {
        const cfg = vscode.workspace.getConfiguration("nimbusware");
        const runId = String(cfg.get("activeRunId") || "").trim();
        const apiBase = String(cfg.get("apiBase") || "http://127.0.0.1:8765/v1");
        if (!runId) {
            item.hide();
            return;
        }
        try {
            item.text = await fetchRunStatus(apiBase, runId);
            item.tooltip = "Open Maker Progress";
            item.show();
        }
        catch {
            item.text = `Nimbusware ${runId.slice(0, 8)}… offline`;
            item.show();
        }
    };
    context.subscriptions.push(vscode.commands.registerCommand("nimbusware.openMakerProgress", () => {
        const cfg = vscode.workspace.getConfiguration("nimbusware");
        const runId = String(cfg.get("activeRunId") || "").trim();
        const base = String(cfg.get("apiBase") || "http://127.0.0.1:8765/v1").replace(/\/v1$/, "");
        const url = runId ? `${base}/v1/maker/app/#/progress?run_id=${runId}` : `${base}/v1/maker/app/`;
        vscode.env.openExternal(vscode.Uri.parse(url));
    }));
    void refresh();
    pollTimer = setInterval(() => void refresh(), 15000);
    context.subscriptions.push({ dispose: () => clearInterval(pollTimer) });
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("nimbusware")) {
            void refresh();
        }
    }));
}
function deactivate() {
    if (pollTimer) {
        clearInterval(pollTimer);
    }
}
//# sourceMappingURL=extension.js.map