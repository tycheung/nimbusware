import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const chatRunCard = readFileSync(
  resolve(import.meta.dirname, "../static/js/tabs/chat_run_card_ui.js"),
  "utf8",
);
const contractGate = readFileSync(
  resolve(import.meta.dirname, "../static/js/contract_gate_ui.js"),
  "utf8",
);

describe("chat run card contract gate", () => {
  it("renders slice.contract gate card in run cards from timeline", () => {
    expect(chatRunCard).toContain("contractGateFromTimeline");
    expect(chatRunCard).toContain("contractGateCardHtml");
    expect(chatRunCard).toContain('testIdPrefix: "maker-chat"');
    expect(chatRunCard).toContain("refreshChatContractGate");
    expect(contractGate).toContain("-contract-gate");
    expect(contractGate).toContain("slice.contract");
  });
});
