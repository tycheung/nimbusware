const CONVENTIONAL_PREFIXES = ["feat:", "fix:", "chore:", "docs:", "refactor:", "test:"];

export function mountReviewCommitPolicyPanel(root, { setupBundle = "default", messageRegex = "" } = {}) {
  const host = root.querySelector("#rev-git-panel");
  if (!host || setupBundle !== "enterprise") return;
  if (host.querySelector("[data-testid='maker-review-commit-policy']")) return;

  const section = document.createElement("div");
  section.className = "commit-policy-panel";
  section.dataset.testid = "maker-review-commit-policy";

  const label = document.createElement("p");
  label.className = "muted";
  label.textContent = messageRegex
    ? `Commit policy regex: ${messageRegex}`
    : "Commit policy: conventional commits recommended";
  section.appendChild(label);

  const chips = document.createElement("div");
  chips.className = "chip-row";
  chips.dataset.testid = "maker-review-commit-chips";

  const preview = document.createElement("input");
  preview.type = "text";
  preview.className = "commit-preview-input";
  preview.placeholder = "feat(PROJ-123): slice summary";
  preview.dataset.testid = "maker-review-commit-preview";
  preview.value = localStorage.getItem("nimbusware.commitPreview") || "";

  const syncPreview = () => {
    localStorage.setItem("nimbusware.commitPreview", preview.value);
  };
  preview.addEventListener("input", syncPreview);

  for (const prefix of CONVENTIONAL_PREFIXES) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = prefix;
    btn.dataset.testid = `maker-review-commit-chip-${prefix.replace(":", "")}`;
    btn.onclick = () => {
      const cur = preview.value.trim();
      preview.value = cur.startsWith(prefix) ? cur : `${prefix} ${cur}`.trim();
      syncPreview();
    };
    chips.appendChild(btn);
  }

  const ticketBtn = document.createElement("button");
  ticketBtn.type = "button";
  ticketBtn.className = "chip";
  ticketBtn.textContent = "PROJ-123";
  ticketBtn.dataset.testid = "maker-review-commit-chip-ticket";
  ticketBtn.onclick = () => {
    const cur = preview.value.trim();
    if (/\([A-Z]+-\d+\)/.test(cur)) {
      preview.value = cur;
    } else if (cur.includes(":")) {
      const [head, ...rest] = cur.split(":");
      preview.value = `${head}(PROJ-123): ${rest.join(":").trim()}`.trim();
    } else {
      preview.value = `(PROJ-123) ${cur}`.trim();
    }
    syncPreview();
  };
  chips.appendChild(ticketBtn);

  section.appendChild(chips);
  section.appendChild(preview);
  host.appendChild(section);
}
