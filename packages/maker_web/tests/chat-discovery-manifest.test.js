import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { plainManifestApprovalText } from "../static/js/tabs/chat_discovery_ui.js";

const discoveryJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/chat_discovery_ui.js"),
  "utf8",
);
const composerJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/chat_composer_ui.js"),
  "utf8",
);

describe("plain manifest approval", () => {
  it("renders human-readable approval line", () => {
    const text = plainManifestApprovalText(
      { surfaces: ["api", "web"], stacks: { api: "fastapi_python", web: "react_vite" } },
      {},
    );
    expect(text).toContain("REST API");
    expect(text).toContain("web UI");
    expect(text).toContain("automated tests");
  });

  it("wires scope confirm and campaign profile remap", () => {
    expect(discoveryJs).toContain("maker-chat-scope-confirm");
    expect(discoveryJs).toContain("plainManifestApprovalText");
    expect(composerJs).toContain("safe_coding_campaign_fullstack");
    expect(composerJs).toContain("workflowProfileForStart");
  });
});
