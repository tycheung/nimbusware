import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const cardJs = readFileSync(join(root, "static/js/tabs/chat_run_card_ui.js"), "utf8");

describe("chat dev preview", () => {
  it("exports preview URL helper and open preview test id", () => {
    expect(cardJs).toContain("export function previewUrlFromDevEnvStatus");
    expect(cardJs).toContain("maker-chat-open-preview");
    expect(cardJs).toContain("frontend_base_url");
  });
});
