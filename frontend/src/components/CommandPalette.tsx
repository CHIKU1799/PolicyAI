"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  ShieldAlert,
  Share2,
  TriangleAlert,
  ShieldCheck,
  FileText,
  ListChecks,
  BookOpen,
  Sparkles,
  Search,
  CornerDownLeft,
} from "lucide-react";
import { getSupabase } from "@/lib/supabase";

type Cmd = {
  id: string;
  label: string;
  hint?: string;
  icon: typeof LayoutDashboard;
  run: (router: ReturnType<typeof useRouter>) => void;
};

const NAV: Cmd[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, run: (r) => r.push("/dashboard") },
  { id: "obligations", label: "Obligations", icon: ShieldAlert, run: (r) => r.push("/obligations") },
  { id: "graph", label: "Knowledge Graph", icon: Share2, run: (r) => r.push("/graph") },
  { id: "gaps", label: "Gap Analysis", icon: TriangleAlert, run: (r) => r.push("/gaps") },
  { id: "controls", label: "Controls", icon: ShieldCheck, run: (r) => r.push("/controls") },
  { id: "policies", label: "Policies", icon: FileText, run: (r) => r.push("/policies") },
  { id: "tasks", label: "Tasks", icon: ListChecks, run: (r) => r.push("/tasks") },
  { id: "kb", label: "Knowledge Base", icon: BookOpen, run: (r) => r.push("/knowledge-base") },
  { id: "ask", label: "Ask PolicyAI Copilot", hint: "AI", icon: Sparkles, run: (r) => r.push("/ask") },
];

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [obligations, setObligations] = useState<{ id: string; title: string }[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load obligation titles once the palette opens (read-only; RLS allows select).
  useEffect(() => {
    if (!open || obligations.length) return;
    const supabase = getSupabase();
    supabase
      ?.from("obligations")
      .select("id,title")
      .order("created_at", { ascending: false })
      .limit(200)
      .then(({ data }) => setObligations((data as { id: string; title: string }[]) ?? []));
  }, [open, obligations.length]);

  useEffect(() => {
    if (open) {
      setQ("");
      setSel(0);
      setTimeout(() => inputRef.current?.focus(), 20);
    }
  }, [open]);

  const results: Cmd[] = useMemo(() => {
    const term = q.trim().toLowerCase();
    const nav = NAV.filter((c) => !term || c.label.toLowerCase().includes(term));
    const obl: Cmd[] = (term ? obligations.filter((o) => o.title.toLowerCase().includes(term)) : [])
      .slice(0, 6)
      .map((o) => ({
        id: `obl-${o.id}`,
        label: o.title,
        hint: "Obligation",
        icon: ShieldAlert,
        run: (r) => r.push("/obligations"),
      }));
    return [...nav, ...obl];
  }, [q, obligations]);

  useEffect(() => {
    setSel(0);
  }, [q]);

  if (!open) return null;

  const activate = (c?: Cmd) => {
    if (!c) return;
    onClose();
    c.run(router);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 pt-[12vh] backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[560px] overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setSel((s) => Math.min(s + 1, results.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setSel((s) => Math.max(s - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            activate(results[sel]);
          } else if (e.key === "Escape") {
            onClose();
          }
        }}
      >
        <div className="flex items-center gap-2.5 border-b border-[var(--border)] px-4 py-3">
          <Search size={16} className="text-[var(--muted-2)]" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search pages, obligations…"
            className="flex-1 bg-transparent text-[14px] outline-none placeholder:text-[var(--muted-2)]"
          />
          <span className="rounded-[5px] border border-[var(--border)] px-1.5 py-px text-[11px] text-[var(--muted-3)]">
            esc
          </span>
        </div>
        <div className="max-h-[52vh] overflow-y-auto p-1.5">
          {results.length === 0 && (
            <div className="px-3 py-6 text-center text-[13px] text-[var(--muted)]">No matches.</div>
          )}
          {results.map((c, i) => (
            <button
              key={c.id}
              onMouseEnter={() => setSel(i)}
              onClick={() => activate(c)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-[13.5px] ${
                i === sel ? "bg-[rgba(75,64,196,0.09)] text-[var(--brand)]" : "text-[var(--text-2)]"
              }`}
            >
              <c.icon size={16} className="flex-none" />
              <span className="flex-1 truncate">{c.label}</span>
              {c.hint && (
                <span className="rounded bg-[var(--border-soft)] px-1.5 py-0.5 text-[10.5px] font-medium text-[var(--muted)]">
                  {c.hint}
                </span>
              )}
              {i === sel && <CornerDownLeft size={13} className="flex-none text-[var(--muted-3)]" />}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
