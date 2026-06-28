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
const deploy_links_1 = require("./deploy_links");
const discipline_routes_1 = require("./discipline_routes");
const scope_card_1 = require("./scope_card");
let pollTimer;
function apiBase() {
    return String(vscode.workspace.getConfiguration("nimbusware").get("apiBase") || "http://127.0.0.1:8765/v1");
}
function activeRunId() {
    return String(vscode.workspace.getConfiguration("nimbusware").get("activeRunId") || "").trim();
}
function soloHat() {
    return String(vscode.workspace.getConfiguration("nimbusware").get("soloDiscipline") || "").trim();
}
async function fetchRunStatus(apiBaseUrl, runId) {
    const url = `${apiBaseUrl.replace(/\/$/, "")}/runs/${runId}`;
    const resp = await fetch(url);
    if (!resp.ok) {
        return `run ${runId.slice(0, 8)}… (HTTP ${resp.status})`;
    }
    const body = (await resp.json());
    const status = String(body.status || "unknown");
    const gate = body.gate_summary ? ` · ${body.gate_summary}` : "";
    return `Nimbusware ${runId.slice(0, 8)}… ${status}${gate}`;
}
async function fetchRunTimeline(apiBaseUrl, runId) {
    const url = `${apiBaseUrl.replace(/\/$/, "")}/runs/${runId}/timeline`;
    const resp = await fetch(url);
    if (!resp.ok) {
        throw new Error(`timeline HTTP ${resp.status}`);
    }
    const body = (await resp.json());
    return body.events || [];
}
async function promptTextFromEditor() {
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
function activate(context) {
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
        }
        catch {
            item.text = `Nimbusware ${runId.slice(0, 8)}… offline`;
            item.show();
        }
    };
    context.subscriptions.push(vscode.commands.registerCommand("nimbusware.openMakerProgress", () => {
        const runId = activeRunId();
        const base = apiBase().replace(/\/v1$/, "");
        const url = runId ? `${base}/v1/maker/app/#/progress?run_id=${runId}` : `${base}/v1/maker/app/`;
        vscode.env.openExternal(vscode.Uri.parse(url));
    }));
    context.subscriptions.push(vscode.commands.registerCommand("nimbusware.showScopeCard", async () => {
        const text = await promptTextFromEditor();
        if (!text) {
            return;
        }
        try {
            const scope = await (0, scope_card_1.fetchScopeRecommend)(apiBase(), text);
            await (0, scope_card_1.showScopeCard)(scope);
        }
        catch (err) {
            void vscode.window.showErrorMessage(`Scope card failed: ${String(err)}`);
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand("nimbusware.previewDisciplineRoutes", async () => {
        const text = await promptTextFromEditor();
        if (!text) {
            return;
        }
        const routes = (0, discipline_routes_1.disciplineRoutes)(text, soloHat() || undefined);
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
    }));
    context.subscriptions.push(vscode.commands.registerCommand("nimbusware.openDeployLinks", async () => {
        const runId = activeRunId();
        if (!runId) {
            void vscode.window.showWarningMessage("Set nimbusware.activeRunId to open deploy links.");
            return;
        }
        try {
            const events = await fetchRunTimeline(apiBase(), runId);
            const links = (0, deploy_links_1.deployLinksFromTimeline)(events);
            const choices = [];
            if (links.apiUrl)
                choices.push(`API: ${links.apiUrl}`);
            if (links.webUrl)
                choices.push(`Web: ${links.webUrl}`);
            choices.push(`Open Maker deploy cockpit`);
            const picked = await vscode.window.showQuickPick(choices, {
                title: `Deploy (${links.ciStatus}) — ${links.ciDetail}`,
            });
            if (!picked) {
                return;
            }
            if (picked.startsWith("API:")) {
                vscode.env.openExternal(vscode.Uri.parse(links.apiUrl));
            }
            else if (picked.startsWith("Web:")) {
                vscode.env.openExternal(vscode.Uri.parse(links.webUrl));
            }
            else {
                const base = apiBase().replace(/\/v1$/, "");
                vscode.env.openExternal(vscode.Uri.parse(`${base}/v1/maker/app/#/progress?run_id=${runId}`));
            }
        }
        catch (err) {
            void vscode.window.showErrorMessage(`Deploy links failed: ${String(err)}`);
        }
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