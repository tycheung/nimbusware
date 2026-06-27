export const MENTION_DISCIPLINES = [
  { key: "frontend", label: "Frontend", aliases: ["fe", "ui"] },
  { key: "backend", label: "Backend", aliases: ["be", "api"] },
  { key: "qa", label: "QA", aliases: ["test", "quality"] },
  { key: "architect", label: "Architect", aliases: ["arch"] },
  { key: "pm", label: "Product", aliases: ["product"] },
  { key: "devops", label: "DevOps", aliases: ["ops", "infra"] },
];

export function mentionCandidates(query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return [...MENTION_DISCIPLINES];
  return MENTION_DISCIPLINES.filter((d) => {
    if (d.key.startsWith(q) || d.label.toLowerCase().startsWith(q)) return true;
    return (d.aliases || []).some((a) => a.startsWith(q));
  });
}

function mentionQueryAt(text, caret) {
  const before = text.slice(0, caret);
  const at = before.lastIndexOf("@");
  if (at < 0) return null;
  const fragment = before.slice(at + 1);
  if (/\s/.test(fragment)) return null;
  return { at, query: fragment };
}

function insertMention(textarea, at, key) {
  const caret = textarea.selectionStart ?? textarea.value.length;
  const value = textarea.value;
  const before = value.slice(0, at);
  const after = value.slice(caret);
  const mention = `@${key} `;
  textarea.value = `${before}${mention}${after}`;
  const pos = before.length + mention.length;
  textarea.setSelectionRange(pos, pos);
  textarea.focus();
}

export function wireChatMentionAutocomplete(textarea) {
  if (!textarea || textarea.dataset.mentionWired === "1") return;
  textarea.dataset.mentionWired = "1";

  const host = textarea.closest("label") || textarea.parentElement;
  if (host) host.classList.add("chat-mention-host");

  const menu = document.createElement("ul");
  menu.className = "chat-mention-menu";
  menu.hidden = true;
  menu.dataset.testid = "maker-chat-mention-menu";
  host?.appendChild(menu);

  let highlight = 0;
  let open = false;

  const hide = () => {
    menu.hidden = true;
    menu.replaceChildren();
    open = false;
    highlight = 0;
  };

  const render = (items) => {
    menu.replaceChildren();
    if (!items.length) {
      hide();
      return;
    }
    items.forEach((item, idx) => {
      const li = document.createElement("li");
      li.dataset.testid = `maker-chat-mention-${item.key}`;
      li.textContent = `@${item.key} — ${item.label}`;
      if (idx === highlight) li.classList.add("active");
      li.addEventListener("mousedown", (ev) => {
        ev.preventDefault();
        const caret = textarea.selectionStart ?? textarea.value.length;
        const ctx = mentionQueryAt(textarea.value, caret);
        if (!ctx) return;
        insertMention(textarea, ctx.at, item.key);
        hide();
      });
      menu.appendChild(li);
    });
    menu.hidden = false;
    open = true;
  };

  const refresh = () => {
    const caret = textarea.selectionStart ?? textarea.value.length;
    const ctx = mentionQueryAt(textarea.value, caret);
    if (!ctx) {
      hide();
      return;
    }
    const items = mentionCandidates(ctx.query);
    highlight = Math.min(highlight, Math.max(0, items.length - 1));
    render(items);
  };

  textarea.addEventListener("input", refresh);
  textarea.addEventListener("click", refresh);
  textarea.addEventListener("keydown", (ev) => {
    if (!open) return;
    const caret = textarea.selectionStart ?? textarea.value.length;
    const ctx = mentionQueryAt(textarea.value, caret);
    if (!ctx) return;
    const items = mentionCandidates(ctx.query);
    if (!items.length) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      highlight = (highlight + 1) % items.length;
      render(items);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      highlight = (highlight - 1 + items.length) % items.length;
      render(items);
    } else if (ev.key === "Enter" && open) {
      ev.preventDefault();
      insertMention(textarea, ctx.at, items[highlight].key);
      hide();
    } else if (ev.key === "Escape") {
      hide();
    }
  });
  textarea.addEventListener("blur", () => {
    setTimeout(hide, 120);
  });
}
