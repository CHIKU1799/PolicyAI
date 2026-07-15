"use client";

import { useRef, useState } from "react";
import { Send, ExternalLink, Sparkles } from "lucide-react";
import { getSupabase, workerFetch } from "@/lib/supabase";
import ImpactAssessment from "@/components/ImpactAssessment";
import Markdown from "@/components/Markdown";

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

  // Mutate only the trailing (assistant) message — the one we're streaming into.
  function updateLast(fn: (m: Msg) => Msg) {
    setMessages((arr) => arr.map((m, i) => (i === arr.length - 1 ? fn(m) : m)));
  }
  const scrollSoon = () =>
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 0);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }, { role: "assistant", text: "" }]);
    setBusy(true);
    try {
      const resp = await workerFetch("/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!resp.ok || !resp.body) throw new Error(`worker responded ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let streamed = false;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const chunks = buf.split("\n\n");
        buf = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const line = chunk.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          let evt: { type: string; text?: string; citations?: Citation[]; message?: string };
          try {
            evt = JSON.parse(line.slice(5).trim());
          } catch {
            continue;
          }
          if (evt.type === "token" && evt.text) {
            streamed = true;
            updateLast((m) => ({ ...m, text: m.text + evt.text }));
          } else if (evt.type === "citations") {
            updateLast((m) => ({ ...m, citations: evt.citations ?? [] }));
          } else if (evt.type === "error") {
            // A structured provider error (rate limit, outage) is a real answer
            // to show, not a reason to retry through the fallback endpoint.
            streamed = true;
            updateLast((m) => ({
              ...m,
              text: m.text || `The Copilot couldn't complete this request: ${evt.message}`,
            }));
          }
        }
        scrollSoon();
      }
      if (!streamed) throw new Error("empty stream");
    } catch {
      // Fall back to the non-streaming endpoint if streaming is unavailable.
      try {
        const resp = await workerFetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q }),
        });
        if (!resp.ok) throw new Error(`worker responded ${resp.status}`);
        const data = await resp.json();
        updateLast((m) => ({ ...m, text: data.answer, citations: data.citations ?? [] }));
      } catch {
        // Final fallback: the serverless backup Copilot bundled with the
        // frontend (free-model chain, grounded via Supabase under the
        // caller's own permissions).
        try {
          const supabase = getSupabase();
          const {
            data: { session },
          } = (await supabase?.auth.getSession()) ?? { data: { session: null } };
          const resp = await fetch("/api/ask", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
            },
            body: JSON.stringify({ question: q }),
          });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data?.detail ?? `backup responded ${resp.status}`);
          updateLast((m) => ({ ...m, text: data.answer, citations: data.citations ?? [] }));
        } catch (err3) {
          updateLast((m) => ({
            ...m,
            text: `The Copilot is unreachable right now (${(err3 as Error).message}).`,
          }));
        }
      }
    } finally {
      setBusy(false);
      scrollSoon();
    }
  }

  const lastEmpty =
    busy && messages.length > 0 && messages[messages.length - 1].text === "";

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && <ImpactAssessment />}
        {messages.length === 0 && (
          <div className="card p-6">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
              <Sparkles size={16} className="text-[var(--brand)]" /> Try asking
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-left text-sm text-slate-600 hover:border-[var(--brand)] hover:text-slate-900"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "assistant" && m.text === "" ? null : (
            <div key={i} className={m.role === "user" ? "flex justify-end" : "flex gap-2.5"}>
              {m.role === "assistant" && (
                <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-[#4b40c4] to-[#23204A] text-white">
                  <Sparkles size={14} />
                </div>
              )}
              <div
                className={
                  m.role === "user"
                    ? "max-w-[80%] rounded-2xl bg-[#4b40c4] px-4 py-2.5 text-sm text-white"
                    : "card min-w-0 max-w-[90%] px-4 py-3"
                }
              >
                {m.role === "user" ? (
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.text}</div>
                ) : (
                  <Markdown>{m.text}</Markdown>
                )}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 border-t border-[var(--border)] pt-2">
                    <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                      Sources
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {m.citations.map((c, j) => (
                        <a
                          key={j}
                          href={c.source_url}
                          target="_blank"
                          rel="noreferrer"
                          title={c.title}
                          className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-[var(--border)] bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:border-[#4b40c4] hover:text-[#4b40c4]"
                        >
                          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#4b40c4] text-[9px] font-bold text-white">
                            {j + 1}
                          </span>
                          <span className="truncate">{c.title}</span>
                          <span className="shrink-0 rounded bg-slate-200 px-1 text-[9px] font-semibold uppercase text-slate-600">
                            {c.source}
                          </span>
                          <ExternalLink size={10} className="shrink-0" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        )}
        {lastEmpty && (
          <div className="card max-w-[90%] px-4 py-3 text-sm text-[var(--muted)]">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--brand)]" />
              Querying your regulations and obligations…
            </span>
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
          className="flex-1 rounded-lg border border-[var(--border)] bg-white px-4 py-2.5 text-sm outline-none focus:border-[var(--brand)]"
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
