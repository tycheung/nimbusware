export const CHAT_INTENT_HINTS = {
  patch: "Describe the bug or paste a failing test name…",
  slice: "Describe the feature to add or change…",
  factory: "Describe the app you want (e.g. todo app with web UI and API)…",
  campaign: "Describe the product you want built end-to-end…",
  self_evolve:
    "Self evolve — optionally name a domain (e.g. accounting software) to study…",
  quick: "Describe a quick local spike or experiment…",
};

export function applyChatIntentPlaceholder(msgEl, intent) {
  if (msgEl && intent && CHAT_INTENT_HINTS[intent]) {
    msgEl.placeholder = CHAT_INTENT_HINTS[intent];
  }
}
