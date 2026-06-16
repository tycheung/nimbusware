export function appendTheaterLine(container, msg, { testid, lineClass = "theater-line" } = {}) {
  if (!container || !msg) return null;
  const li = document.createElement("li");
  li.className = `${lineClass} severity-${msg.severity || "info"}`;
  if (msg.store_seq != null) {
    const pick = document.createElement("input");
    pick.type = "checkbox";
    pick.dataset.theaterPick = "1";
    pick.dataset.storeSeq = String(msg.store_seq);
    li.appendChild(pick);
  }
  const seq = msg.store_seq != null ? `#${msg.store_seq} ` : "";
  const headline = document.createElement("div");
  headline.className = "theater-headline";
  headline.textContent = `${seq}${msg.actor_display || "System"}: ${msg.headline || msg.message || ""}`;
  if (testid || msg.data_testid) li.dataset.testid = testid || msg.data_testid;
  li.appendChild(headline);
  const body = (msg.body_md || "").trim();
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
  container.appendChild(li);
  return li;
}

export function theaterPayloadFromSse(data) {
  if (!data || typeof data !== "object") return null;
  if (data.headline || data.body_md || data.actor_display) {
    return {
      actor_display: data.actor_display || "System",
      headline: data.headline || data.message || "",
      body_md: data.body_md || "",
      severity: data.severity || (data.message_kind === "gate" ? "block" : "info"),
      message_kind: data.message_kind,
      store_seq: data.store_seq,
      data_testid: data.message_kind === "gate" && data.severity === "block" ? "maker-chat-gate-line" : "maker-chat-theater-line",
    };
  }
  return null;
}
