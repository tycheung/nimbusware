import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type Msg = { role: string; content: string };
type Classification = {
  work_type?: string;
  confidence?: number;
  rationale?: string;
};

const SESSION_KEY = "nimbusware_chat_session";
const WORK_TYPES = ["patch", "slice", "campaign", "factory"] as const;

function chatSessionId(): string {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function workTypeLabel(workType: string): string {
  switch (workType) {
    case "patch":
      return "Patch";
    case "slice":
      return "Micro-slice";
    case "campaign":
      return "Campaign";
    case "factory":
      return "Factory";
    default:
      return workType;
  }
}

export function OperatorChatPage() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: "Operator chat — try /help or describe a change" },
  ]);
  const [input, setInput] = useState("");
  const [classification, setClassification] = useState<Classification | null>(null);

  useEffect(() => {
    chatSessionId();
  }, []);

  async function send(textOverride?: string) {
    const text = (textOverride ?? input).trim();
    if (!text) return;
    if (!textOverride) setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const res = await apiJson<{
        reply: string;
        classification?: Classification | null;
      }>("/admin/ui/operator-chat/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Nimbusware-Chat-Session": chatSessionId(),
        },
        body: JSON.stringify({ text }),
      });
      setClassification(res.classification ?? null);
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: String((e as Error).message || e) }]);
    }
  }

  async function acceptClassification(workType: string) {
    const profile =
      workType === "slice"
        ? "micro_slice"
        : workType === "factory"
          ? "campaign_factory_zero_touch"
          : workType === "campaign"
            ? "campaign_micro_slice"
            : "patch";
    await send(workType === (classification?.work_type ?? "") ? "/run auto" : `/run ${profile}`);
  }

  const wt = classification?.work_type ?? "";
  const confidence =
    classification?.confidence != null ? Math.round(Number(classification.confidence) * 100) : null;

  return (
    <section>
      <h2>Operator chat</h2>
      {classification ? (
        <article class="panel chat-classifier-card" data-testid="admin-chat-classifier-card">
          <h4>
            Suggested: {workTypeLabel(wt)}
            {confidence != null ? ` (${confidence}% confidence)` : ""}
          </h4>
          {classification.rationale ? <p class="muted">{classification.rationale}</p> : null}
          <div class="actions chat-action-chips">
            <button
              type="button"
              class="primary"
              data-testid="admin-chat-accept-chip"
              onClick={() => acceptClassification(wt)}
            >
              Start as {workTypeLabel(wt)}
            </button>
            {WORK_TYPES.filter((alt) => alt !== wt).map((alt) => (
              <button
                key={alt}
                type="button"
                data-testid={`admin-chat-override-chip-${alt}`}
                onClick={() => acceptClassification(alt)}
              >
                {workTypeLabel(alt)}
              </button>
            ))}
          </div>
        </article>
      ) : null}
      <ul class="chat-log">
        {messages.map((m, i) => (
          <li key={i}>
            <strong>{m.role}:</strong> {m.content}
          </li>
        ))}
      </ul>
      <input
        value={input}
        onInput={(e) => setInput((e.target as HTMLInputElement).value)}
        onKeyDown={(e) => e.key === "Enter" && send()}
      />
      <button type="button" onClick={() => send()}>
        Send
      </button>
    </section>
  );
}
