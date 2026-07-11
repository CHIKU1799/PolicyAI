"use client";

import clsx from "clsx";
import { Download } from "lucide-react";
import type { ReactNode } from "react";

export function ExportButton({ onClick, label = "Export CSV" }: { onClick: () => void; label?: string }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-[#4b40c4] hover:text-slate-900"
    >
      <Download size={14} />
      {label}
    </button>
  );
}

// The Topbar now owns the page title + subtitle for every route, so the in-page
// header is intentionally a no-op. Kept as a component so existing pages that
// render <PageHeader/> don't need edits and stay free of duplicate titles.
export function PageHeader(props: { title: string; subtitle?: string }) {
  void props; // intentionally unused: the Topbar renders titles for every route
  return null;
}

export function Kpi({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "danger" | "warn" | "ok";
}) {
  const toneColor = {
    default: "text-[var(--text)]",
    danger: "text-red-600",
    warn: "text-amber-600",
    ok: "text-emerald-600",
  }[tone];
  return (
    <div className="card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </div>
      <div className={clsx("mt-2 text-2xl font-semibold", toneColor)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-[var(--muted)]">{hint}</div>}
    </div>
  );
}

export function Badge({ className, children }: { className?: string; children: ReactNode }) {
  return <span className={clsx("badge", className)}>{children}</span>;
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="text-sm font-semibold text-[var(--text)]">{title}</div>
      <div className="mt-1 max-w-md text-sm text-[var(--muted)]">{body}</div>
    </div>
  );
}

export function DemoBanner() {
  return (
    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
      Supabase isn&apos;t configured yet. Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
      <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to load live data.
    </div>
  );
}
