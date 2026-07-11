"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Search, Sparkles } from "lucide-react";
import AlertFeed from "@/components/AlertFeed";
import CommandPalette from "@/components/CommandPalette";

const TITLES: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Compliance Dashboard", subtitle: "Live posture across regulations, obligations & controls" },
  "/obligations": { title: "Obligations", subtitle: "Structured obligations mapped to controls, policies & tasks" },
  "/gaps": { title: "Gap Analysis", subtitle: "Where your controls and policies fall short of obligations" },
  "/controls": { title: "Controls Testing", subtitle: "Real-time control effectiveness monitoring" },
  "/policies": { title: "Policy Library", subtitle: "Versioning, review & approval with audit traceability" },
  "/tasks": { title: "Tasks", subtitle: "Actionable work generated from obligations" },
  "/knowledge-base": { title: "Knowledge Base", subtitle: "Your company's policies and registrations" },
  "/graph": { title: "Knowledge Graph", subtitle: "How regulations connect to entities, topics & deadlines" },
  "/ask": { title: "Ask PolicyAI", subtitle: "Grounded answers across your regulatory data" },
};

export default function Topbar() {
  const pathname = usePathname();
  const key = Object.keys(TITLES).find((k) => pathname.startsWith(k)) ?? "/dashboard";
  const { title, subtitle } = TITLES[key];
  const [paletteOpen, setPaletteOpen] = useState(false);
  const router = useRouter();

  // Global shortcuts: ⌘K command palette, ⌘J jump to the Copilot.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      const k = e.key.toLowerCase();
      if (k === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      } else if (k === "j") {
        e.preventDefault();
        router.push("/ask");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return (
    <header className="flex h-[60px] flex-none items-center gap-4 border-b border-[var(--border)] bg-[rgba(252,252,251,.82)] px-6 backdrop-blur-md">
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <div className="flex-none">
        <div className="serif text-[19px] font-medium leading-tight tracking-[-.01em]">{title}</div>
        <div className="mt-0.5 text-[12px] text-[#8b8e95]">{subtitle}</div>
      </div>

      <div className="flex flex-1 justify-center">
        <button
          onClick={() => setPaletteOpen(true)}
          className="flex h-[38px] w-[360px] max-w-full items-center gap-2.5 rounded-[10px] border border-[var(--border)] bg-[#f2f2ef] px-3.5 text-[var(--muted-2)] transition-colors hover:border-[var(--brand)]/40 hover:bg-white"
        >
          <Search size={15} />
          <span className="text-[13px]">Search regulations, obligations, controls…</span>
          <span className="ml-auto rounded-[5px] border border-[#e2e2dd] px-1.5 py-px text-[11px] font-semibold text-[var(--muted-3)]">
            ⌘K
          </span>
        </button>
      </div>

      <div className="flex flex-none items-center gap-2.5">
        <AlertFeed />
        <Link
          href="/ask"
          className="brand-grad flex h-[38px] items-center gap-2 rounded-[10px] px-[15px] text-[13px] font-semibold text-white shadow-[0_2px_8px_rgba(67,56,184,.32)]"
        >
          <Sparkles size={16} />
          Ask PolicyAI
        </Link>
      </div>
    </header>
  );
}
