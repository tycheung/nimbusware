import * as vscode from "vscode";

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function plainManifestApprovalText(manifest: Record<string, unknown> | null, state?: Record<string, unknown>): string {
  if (!manifest || typeof manifest !== "object") {
    return "";
  }
  const surfaces = Array.isArray(manifest.surfaces) ? (manifest.surfaces as string[]) : [];
  const stacks =
    manifest.stacks && typeof manifest.stacks === "object"
      ? (manifest.stacks as Record<string, string>)
      : {};
  const productParts: string[] = [];
  if (surfaces.includes("web")) productParts.push("web UI");
  if (surfaces.includes("api")) productParts.push("REST API");
  if (surfaces.includes("contract")) productParts.push("shared contracts");
  const stackParts: string[] = [];
  if (stacks.web) stackParts.push(`${stacks.web} frontend`);
  if (stacks.api) stackParts.push(`${stacks.api} backend`);
  const product = productParts.length ? productParts.join(" + ") : "full-stack app";
  const stackLine = stackParts.length ? ` (${stackParts.join(", ")})` : "";
  const lead = state?.recommend_for_me ? "Recommended plan" : "You are approving";
  return `${lead}: ${product}${stackLine} with automated tests`;
}

export async function fetchScopeRecommend(apiBase: string, prompt: string): Promise<Record<string, unknown>> {
  const url = `${apiBase.replace(/\/$/, "")}/chat/scope/recommend`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ business_prompt: prompt }),
  });
  if (!resp.ok) {
    throw new Error(`scope recommend HTTP ${resp.status}`);
  }
  const body = (await resp.json()) as { scope?: Record<string, unknown> };
  return body.scope || {};
}

export async function showScopeCard(scope: Record<string, unknown>): Promise<void> {
  const manifest = (scope.stack_manifest as Record<string, unknown> | undefined) || null;
  const plain = plainManifestApprovalText(manifest, scope);
  const surfaces = Array.isArray(manifest?.surfaces) ? (manifest?.surfaces as string[]).join(", ") : "";
  const stacks =
    manifest?.stacks && typeof manifest.stacks === "object"
      ? Object.entries(manifest.stacks as Record<string, string>)
          .map(([k, v]) => `${k}: ${v}`)
          .join("; ")
      : "";
  const panel = vscode.window.createWebviewPanel(
    "nimbuswareScope",
    "Nimbusware scope",
    vscode.ViewColumn.Beside,
    { enableScripts: false },
  );
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
