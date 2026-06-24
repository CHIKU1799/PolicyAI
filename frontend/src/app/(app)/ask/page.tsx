"use client";

import { useRef, useState } from "react";
import { Send, ExternalLink, Sparkles } from "lucide-react";
import { WORKER_URL } from "@/lib/supabase";
import { PageHeader } from "@/components/ui";

interface Citation {
  title: string;
  source_url: string;
  source: string;
}
interface Msg {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

const SUGGESTIONS = [
  "What obligations are open and high severity?",
  "What compliance tasks are overdue?",
  "What changed in microfinance pricing rules?",
  "What is our company's regulatory profile?",
];

export default function AskPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const resp = await fetch(`${WORKER_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!resp.ok) throw new Error(`worker responded ${resp.status}`);
      const data = await resp.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.answer, citations: data.citations ?? [] },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Couldn't reach the worker (${(err as Error).message}).` },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <PageHeader
        title="Ask PolicyAI"
        subtitle="Plain-English answers grounded in your regulations, obligations, and tasks — with sources."
      />

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <div className="card p-6">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
              <Sparkles size={16} className="text-blue-500" /> Try asking
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-left text-sm text-slate-600 hover:border-blue-400 hover:text-slate-900"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
            <div
              className={
                m.role === "user"
                  ? "max-w-[80%] rounded-2xl bg-[#4b40c4] px-4 py-2.5 text-sm text-white"
                  : "card max-w-[90%] px-4 py-3 text-sm text-slate-800"
              }
            >
              <div className="whitespace-pre-wrap leading-relaxed">{m.text}</div>
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 border-t border-[var(--border)] pt-2">
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                    Sources
                  </div>
                  <ul className="space-y-1">
                    {m.citations.map((c, j) => (
                      <li key={j}>
                        <a
                          href={c.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                        >
                          <span className="rounded bg-slate-100 px-1 font-medium uppercase">
                            {c.source}
                          </span>
                          {c.title}
                          <ExternalLink size={11} />
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="card max-w-[90%] px-4 py-3 text-sm text-[var(--muted)]">
            Thinking… querying your regulations and obligations.
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="sticky bottom-0 flex items-center gap-2 border-t border-[var(--border)] bg-[var(--bg)] py-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about obligations, deadlines, or what changed…"
          disabled={busy}
          className="flex-1 rounded-lg border border-[var(--border)] bg-white px-4 py-2.5 text-sm outline-none focus:border-blue-400"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-[#4b40c4] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#3a2fb0] disabled:opacity-60"
        >
          <Send size={16} />
          Ask
        </button>
      </form>
    </div>
  );
}
