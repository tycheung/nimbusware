import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { mentionCandidates, MENTION_DISCIPLINES } from "../static/js/chat_mention_ui.js";

const mentionJs = readFileSync(resolve(import.meta.dirname, "../static/js/chat_mention_ui.js"), "utf8");

describe("chat mention autocomplete", () => {
  it("lists all disciplines when query is empty", () => {
    expect(mentionCandidates("")).toHaveLength(MENTION_DISCIPLINES.length);
  });

  it("filters by key and alias", () => {
    expect(mentionCandidates("fe").map((d) => d.key)).toContain("frontend");
    expect(mentionCandidates("ops").map((d) => d.key)).toContain("devops");
  });

  it("exports menu wiring for chat composer", () => {
    expect(mentionJs).toContain("maker-chat-mention-menu");
    expect(mentionJs).toContain("wireChatMentionAutocomplete");
  });
});
