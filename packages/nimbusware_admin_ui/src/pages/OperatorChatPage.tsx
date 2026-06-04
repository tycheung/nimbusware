import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type Msg = { role: string; content: string };

const SESSION_KEY = "nimbusware_chat_session";

function chatSessionId(): string {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function OperatorChatPage() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: "Operator chat — try /help or /run micro_slice" },
  ]);
  const [input, setInput] = useState("");

  useEffect(() => {
    chatSessionId();
  }, []);

  async function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const res = await apiJson<{ reply: string }>("/admin/ui/operator-chat/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Nimbusware-Chat-Session": chatSessionId(),
        },
        body: JSON.stringify({ text }),
      });
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: String((e as Error).message || e) }]);
    }
  }

  return (
    <section>
      <h2>Operator chat</h2>
      <ul class="chat-log">
        {messages.map((m, i) => (
          <li key={i}>
            <strong>{m.role}:</strong> {m.content}
          </li>
        ))}
      </ul>
      <input value={input} onInput={(e) => setInput((e.target as HTMLInputElement).value)} onKeyDown={(e) => e.key === "Enter" && send()} />
      <button type="button" onClick={send}>
        Send
      </button>
    </section>
  );
}
