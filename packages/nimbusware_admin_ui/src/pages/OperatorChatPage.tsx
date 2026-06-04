import { useState } from "preact/hooks";

type Msg = { role: string; content: string };

export function OperatorChatPage() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: "Operator chat — try /help or /run micro_slice" },
  ]);
  const [input, setInput] = useState("");

  async function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    const res = await fetch("/v1/runs", { method: "OPTIONS" }).catch(() => null);
    const hint =
      text.startsWith("/") ?
        `Command \`${text}\` — wire to operator_chat_core via a small BFF when needed.`
      : "Natural language steering — use /run micro_slice to start a run via API.";
    void res;
    setMessages((m) => [...m, { role: "assistant", content: hint }]);
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
      <input value={input} onInput={(e) => setInput((e.target as HTMLInputElement).value)} />
      <button type="button" onClick={send}>
        Send
      </button>
    </section>
  );
}
