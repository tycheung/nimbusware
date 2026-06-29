import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const soloJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/settings_solo_discipline_ui.js"),
  "utf8",
);
const hatChipsJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/chat_solo_hat_ui.js"),
  "utf8",
);
const chatShellJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/chat_shell_html.js"),
  "utf8",
);
const inviteJs = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/chat_invite_modal_ui.js"),
  "utf8",
);

describe("solo discipline and invite templates", () => {
  it("settings panel stores solo hat", () => {
    expect(soloJs).toContain("maker-settings-solo-discipline");
    expect(soloJs).toContain("maker_solo_discipline");
  });

  it("chat composer exposes solo hat quick-switch chips", () => {
    expect(chatShellJs).toContain("maker-chat-solo-hat-chips");
    expect(hatChipsJs).toContain("maker-chat-solo-hat-${hat.id}");
    expect(hatChipsJs).toContain("maker-solo-discipline-changed");
  });

  it("invite modal exposes roster templates", () => {
    expect(inviteJs).toContain("maker-chat-invite-template");
    expect(inviteJs).toContain("pair-devs-qa");
    expect(inviteJs).toContain("full-team");
  });
});
