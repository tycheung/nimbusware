export const CHAT_INTENT_HINTS = {
  patch: "Describe the bug or paste a failing test name…",
  slice: "Describe the feature to add or change…",
  factory: "Describe the app you want (e.g. todo app with web UI and API)…",
  campaign: "Describe the product you want built end-to-end…",
};

export function applyChatIntentPlaceholder(msgEl, intent) {
  if (msgEl && intent && CHAT_INTENT_HINTS[intent]) {
    msgEl.placeholder = CHAT_INTENT_HINTS[intent];
  }
}
