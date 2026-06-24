"use client";

import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getSupabase } from "@/lib/supabase";
import { PageHeader, Badge, DemoBanner, EmptyState } from "@/components/ui";
import { SEVERITY_STYLES, type Obligation } from "@/lib/types";

export default function ObligationsPage() {
  const [configured, setConfigured] = useState(true);
  const [rows, setRows] = useState<Obligation[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [severity, setSeverity] = useState<string>("all");

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    supabase
      .from("obligations")
      .select("*")
      .order("created_at", { ascending: false })
      .then(({ data }) => setRows((data as Obligation[]) ?? []));
  }, []);

  const filtered = severity === "all" ? rows : rows.filter((r) => r.severity === severity);

  return (
    <div>
      <PageHeader
        title="Obligations"
        subtitle="Requirements mapped from new regulations to your company's profile"
      />
      {!configured && <DemoBanner />}

      <div className="mb-4 flex gap-2">
        {["all", "critical", "high", "medium", "low"].map((s) => (
          <button
            key={s}
            onClick={() => setSeverity(s)}
            className={`rounded-full border px-3 py-1 text-xs font-medium capitalize ${
              severity === s
                ? "border-[#4b40c4] bg-[#4b40c4] text-white"
                : "border-[var(--border)] bg-white text-[var(--muted)]"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No obligations to show"
          body="As the monitoring agent ingests new regulations and maps them to your knowledge base, obligations land here with gap analysis and tasks."
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="w-8 px-4 py-3"></th>
                <th className="px-4 py-3">Obligation</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filtered.map((o) => (
                <Fragment key={o.id}>
                  <tr
                    className="cursor-pointer hover:bg-slate-50"
                    onClick={() => setOpen(open === o.id ? null : o.id)}
                  >
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {open === o.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">{o.title}</div>
                      <div className="line-clamp-1 text-xs text-[var(--muted)]">{o.summary}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={SEVERITY_STYLES[o.severity]}>{o.severity}</Badge>
                    </td>
                    <td className="px-4 py-3 capitalize text-[var(--muted)]">{o.status}</td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {new Date(o.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                  {open === o.id && (
                    <tr className="bg-slate-50/60">
                      <td></td>
                      <td colSpan={4} className="px-4 py-4">
                        <Detail label="Summary" value={o.summary} />
                        <Detail label="What changed" value={o.what_changed} />
                        <Detail label="Gap analysis" value={o.gap_analysis} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="mb-3 last:mb-0">
      <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-sm text-slate-700">{value}</div>
    </div>
  );
}
