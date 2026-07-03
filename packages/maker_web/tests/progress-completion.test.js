import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

describe("progress theater and completion", () => {
  it("progress theater uses structured payloads with evidence toggle", () => {
    const progressJs = readFileSync(join(root, "static/js/tabs/progress.js"), "utf8");
    expect(progressJs).toContain("theaterPayloadFromSse");
    expect(progressJs).toContain("handleProgressTheaterEvent");
    expect(progressJs).not.toContain("theaterLineText(data)");
  });

  it("completion cockpit has plain-language terminal headline", () => {
    const chipsJs = readFileSync(join(root, "static/js/tabs/progress/render-chips.js"), "utf8");
    expect(chipsJs).toContain("completionHeadline");
    expect(chipsJs).toContain("launch-ready");
    expect(chipsJs).toContain("completion-terminal--ready");
  });

  it("auto launch check runs once on terminal campaign", () => {
    const progressJs = readFileSync(join(root, "static/js/tabs/progress.js"), "utf8");
    expect(progressJs).toContain("maybeAutoLaunchCheck");
    expect(progressJs).toContain("maker/launch-eval");
  });
});
