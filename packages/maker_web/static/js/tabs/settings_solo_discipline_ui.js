const STORAGE_KEY = "maker_solo_discipline";

export const SOLO_DISCIPLINES = [
  { id: "", label: "None (broadcast)" },
  { id: "pm", label: "Product (PM)" },
  { id: "architect", label: "Architect" },
  { id: "frontend", label: "Frontend" },
  { id: "backend", label: "Backend" },
  { id: "qa", label: "QA" },
  { id: "devops", label: "DevOps" },
];

export function readSoloDiscipline() {
  return localStorage.getItem(STORAGE_KEY)?.trim() || "";
}

export function writeSoloDiscipline(value) {
  const val = String(value || "").trim();
  if (val) localStorage.setItem(STORAGE_KEY, val);
  else localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(
    new CustomEvent("maker-solo-discipline-changed", { detail: { value: val } }),
  );
}

export function soloDisciplineSectionHtml() {
  return `
    <section id="settings-solo-discipline" class="panel" data-testid="maker-settings-solo-discipline">
      <h3>Solo discipline hat</h3>
      <p class="muted">Wear one role when working alone — routes feedback like <code>@frontend</code> without a collab session.</p>
      <label>
        Active hat
        <select id="settings-solo-discipline-select" data-testid="maker-settings-solo-discipline-select">
          ${SOLO_DISCIPLINES.map((d) => `<option value="${d.id}">${d.label}</option>`).join("")}
        </select>
      </label>
    </section>`;
}

export function wireSoloDisciplinePanel(root) {
  const select = root.querySelector("#settings-solo-discipline-select");
  if (!select) return;
  const current = readSoloDiscipline();
  if (current) select.value = current;
  select.addEventListener("change", () => writeSoloDiscipline(select.value));
}
