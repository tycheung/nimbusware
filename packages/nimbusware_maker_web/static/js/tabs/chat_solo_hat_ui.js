import {
  readSoloDiscipline,
  SOLO_DISCIPLINES,
  writeSoloDiscipline,
} from "./settings_solo_discipline_ui.js";

const HAT_CHIPS = SOLO_DISCIPLINES.filter((d) => d.id);

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
