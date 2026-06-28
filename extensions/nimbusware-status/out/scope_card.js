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
exports.plainManifestApprovalText = plainManifestApprovalText;
exports.fetchScopeRecommend = fetchScopeRecommend;
exports.showScopeCard = showScopeCard;
const vscode = __importStar(require("vscode"));
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
function plainManifestApprovalText(manifest, state) {
    if (!manifest || typeof manifest !== "object") {
        return "";
    }
    const surfaces = Array.isArray(manifest.surfaces) ? manifest.surfaces : [];
    const stacks = manifest.stacks && typeof manifest.stacks === "object"
        ? manifest.stacks
        : {};
    const productParts = [];
    if (surfaces.includes("web"))
        productParts.push("web UI");
    if (surfaces.includes("api"))
        productParts.push("REST API");
    if (surfaces.includes("contract"))
        productParts.push("shared contracts");
    const stackParts = [];
    if (stacks.web)
        stackParts.push(`${stacks.web} frontend`);
    if (stacks.api)
        stackParts.push(`${stacks.api} backend`);
    const product = productParts.length ? productParts.join(" + ") : "full-stack app";
    const stackLine = stackParts.length ? ` (${stackParts.join(", ")})` : "";
    const lead = state?.recommend_for_me ? "Recommended plan" : "You are approving";
    return `${lead}: ${product}${stackLine} with automated tests`;
}
async function fetchScopeRecommend(apiBase, prompt) {
    const url = `${apiBase.replace(/\/$/, "")}/chat/scope/recommend`;
    const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ business_prompt: prompt }),
    });
    if (!resp.ok) {
        throw new Error(`scope recommend HTTP ${resp.status}`);
    }
    const body = (await resp.json());
    return body.scope || {};
}
async function showScopeCard(scope) {
    const manifest = scope.stack_manifest || null;
    const plain = plainManifestApprovalText(manifest, scope);
    const surfaces = Array.isArray(manifest?.surfaces) ? (manifest?.surfaces).join(", ") : "";
    const stacks = manifest?.stacks && typeof manifest.stacks === "object"
        ? Object.entries(manifest.stacks)
            .map(([k, v]) => `${k}: ${v}`)
            .join("; ")
        : "";
    const panel = vscode.window.createWebviewPanel("nimbuswareScope", "Nimbusware scope", vscode.ViewColumn.Beside, { enableScripts: false });
    panel.webview.html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { font-family: var(--vscode-font-family); padding: 1rem; color: var(--vscode-foreground); }
h2 { margin-top: 0; }
.muted { opacity: 0.8; font-size: 0.9em; }
</style></head><body>
<h2>Scope manifest</h2>
<p>${escapeHtml(plain || "No manifest yet — run scope discovery in Maker Chat.")}</p>
${surfaces ? `<p class="muted">Surfaces: ${escapeHtml(surfaces)}</p>` : ""}
${stacks ? `<p class="muted">Stacks: ${escapeHtml(stacks)}</p>` : ""}
</body></html>`;
}
//# sourceMappingURL=scope_card.js.map