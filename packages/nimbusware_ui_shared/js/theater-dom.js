/**
 * Append one theater line to a list element (framework-agnostic DOM).
 * @param {HTMLElement} list
 * @param {Record<string, unknown>} msg
 * @param {{ pickable?: boolean }} [options]
 */
export function appendTheaterLine(list, msg, { pickable = true } = {}) {
  if (!list || !msg) return;
  const li = document.createElement("li");
  li.className = `theater-line severity-${msg.severity || "info"}`;
  if (
    msg.data_testid?.includes("compaction") ||
    (msg.message_kind === "context" && /compact/i.test(String(msg.headline || "")))
  ) {
    li.classList.add("theater-line--compaction");
  }
  if (pickable && msg.store_seq != null) {
    const pick = document.createElement("input");
    pick.type = "checkbox";
    pick.dataset.theaterPick = "1";
    pick.dataset.storeSeq = String(msg.store_seq);
    li.appendChild(pick);
  }
  const seq = msg.store_seq != null ? `#${msg.store_seq} ` : "";
  const headline = document.createElement("div");
  headline.className = "theater-headline";
  headline.textContent = `${seq}${msg.actor_display || "System"}: ${msg.headline || ""}`;
  if (msg.data_testid) li.dataset.testid = msg.data_testid;
  li.appendChild(headline);
  const body = String(msg.body_md || "").trim();
  if (body) {
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "linkish theater-evidence-toggle";
    toggle.textContent = "Evidence";
    const pre = document.createElement("pre");
    pre.className = "theater-body";
    pre.hidden = true;
    pre.textContent = body;
    toggle.addEventListener("click", () => {
      pre.hidden = !pre.hidden;
      toggle.textContent = pre.hidden ? "Evidence" : "Hide";
    });
    headline.appendChild(document.createTextNode(" "));
    headline.appendChild(toggle);
    li.appendChild(pre);
  }
  list.appendChild(li);
}
