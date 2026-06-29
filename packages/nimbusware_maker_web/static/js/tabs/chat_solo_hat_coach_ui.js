import { archetypeSubchoice } from "../archetype-picker.js";

const SOLO_HAT_COACH_KEY = "maker_solo_hat_coach_dismissed";

export function mountSoloHatCoachHint(root) {
  if (localStorage.getItem(SOLO_HAT_COACH_KEY) === "1") return;
  if (archetypeSubchoice() !== "engineer") return;
  if (root.querySelector("[data-testid='maker-chat-solo-hat-coach']")) return;

  const chips = root.querySelector("#chat-solo-hat-chips");
  if (!chips) return;

  const hint = document.createElement("aside");
  hint.className = "panel chat-solo-hat-coach";
  hint.dataset.testid = "maker-chat-solo-hat-coach";

  const p = document.createElement("p");
  p.innerHTML =
    "<strong>Wear multiple hats</strong> — pick a solo discipline above when you work alone. " +
    "Your messages route like <code>@frontend</code> or <code>@architect</code> without typing mentions. " +
    "Use <strong>Broadcast</strong> to clear the hat, or set a default in Settings.";
  hint.appendChild(p);

  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "linkish";
  dismiss.textContent = "Got it";
  dismiss.dataset.testid = "maker-chat-solo-hat-coach-dismiss";
  dismiss.addEventListener("click", () => {
    localStorage.setItem(SOLO_HAT_COACH_KEY, "1");
    hint.remove();
  });
  hint.appendChild(dismiss);

  chips.insertAdjacentElement("afterend", hint);
}
