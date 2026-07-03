import { archetypeSubchoice } from "../archetype-picker.js";
import {
  readSoloDiscipline,
  SOLO_DISCIPLINES,
  writeSoloDiscipline,
} from "./settings_solo_discipline_ui.js";

const HAT_CHIPS = SOLO_DISCIPLINES.filter((d) => d.id);
const SOLO_HAT_COACH_KEY = "maker_solo_hat_coach_dismissed";

function syncActiveChip(mount, activeId) {
  for (const btn of mount.querySelectorAll("[data-solo-hat]")) {
    const on = btn.dataset.soloHat === activeId;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  }
}

export function mountSoloHatChips(root) {
  const mount = root.querySelector("#chat-solo-hat-chips");
  if (!mount) return;

  mount.replaceChildren();
  const caption = document.createElement("span");
  caption.className = "muted chat-solo-hat-caption";
  caption.textContent = "Solo hat:";
  mount.appendChild(caption);

  for (const hat of HAT_CHIPS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "secondary chat-solo-hat-chip";
    btn.dataset.soloHat = hat.id;
    btn.dataset.testid = `maker-chat-solo-hat-${hat.id}`;
    btn.textContent = hat.label;
    btn.title = `Wear ${hat.label} — routes feedback like @${hat.id}`;
    btn.addEventListener("click", () => {
      const next = readSoloDiscipline() === hat.id ? "" : hat.id;
      writeSoloDiscipline(next);
      syncActiveChip(mount, next);
    });
    mount.appendChild(btn);
  }

  const clear = document.createElement("button");
  clear.type = "button";
  clear.className = "linkish chat-solo-hat-clear";
  clear.dataset.testid = "maker-chat-solo-hat-none";
  clear.textContent = "Broadcast";
  clear.title = "Clear solo hat (no default @ routing)";
  clear.addEventListener("click", () => {
    writeSoloDiscipline("");
    syncActiveChip(mount, "");
  });
  mount.appendChild(clear);

  syncActiveChip(mount, readSoloDiscipline());

  const onChanged = (ev) => syncActiveChip(mount, ev.detail?.value ?? readSoloDiscipline());
  window.addEventListener("maker-solo-discipline-changed", onChanged);
}

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
