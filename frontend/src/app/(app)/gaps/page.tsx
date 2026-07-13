"use client";

import { useEffect, useState } from "react";
import { getSupabase, workerFetch } from "@/lib/supabase";
import { PageHeader, Badge, DemoBanner, ExportButton } from "@/components/ui";
import { toast } from "@/components/Toast";
import { downloadCSV } from "@/lib/export";
import { GAP_COLUMNS, SEVERITY_STYLES, type Gap, type GapStatus } from "@/lib/types";

export default function GapsPage() {
  const [configured, setConfigured] = useState(true);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [coverage, setCoverage] = useState<{ pct: number | null; covered: number; applicable: number; uncovered: number } | null>(null);

  useEffect(() => {
    workerFetch("/insights")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setCoverage(d.coverage ?? null))
      .catch(() => setCoverage(null));
  }, []);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    supabase
      .from("gaps")
      .select("*")
      .order("created_at", { ascending: false })
      .then(({ data }) => setGaps((data as Gap[]) ?? []));
  }, []);

  async function move(gap: Gap, status: GapStatus) {
    const prev = gap.status;
    setGaps((cur) => cur.map((g) => (g.id === gap.id ? { ...g, status } : g)));
    const supabase = getSupabase();
    if (!supabase) return;
    const { error } = await supabase.from("gaps").update({ status }).eq("id", gap.id);
    if (error) {
      setGaps((cur) => cur.map((g) => (g.id === gap.id ? { ...g, status: prev } : g)));
      toast(`Couldn't update gap: ${error.message}`, "error");
    } else {
      toast(`Gap moved to ${status}`);
    }
  }

  return (
    <div>
      <PageHeader
        title="Gap Analysis"
        subtitle="Where your policies, processes and controls fall short of emerging obligations"
      />
      {!configured && <DemoBanner />}

      {coverage?.pct != null && (
        <div className="card mb-4 flex items-center gap-4 p-4">
          <div>
            <div className="text-2xl font-bold text-[#23204A]">{coverage.pct}%</div>
            <div className="text-xs text-[var(--muted)]">requirement coverage</div>
          </div>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#4B40C4] to-[#1F9D5B]"
              style={{ width: `${coverage.pct}%` }}
            />
          </div>
          <div className="text-xs text-[var(--muted)]">
            {coverage.covered.toLocaleString()} of {coverage.applicable.toLocaleString()} applicable
            requirements covered · {coverage.uncovered.toLocaleString()} open
          </div>
        </div>
      )}

      <div className="mb-4 flex justify-end">
        <ExportButton
          label="Export register"
          onClick={() =>
            downloadCSV(
              "gap-register.csv",
              gaps.map((g) => ({
                description: g.description,
                severity: g.severity,
                status: g.status,
                owner: g.owner,
                due_date: g.due_date,
                remediation_plan: g.remediation_plan,
              })),
            )
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {GAP_COLUMNS.map((col) => {
          const items = gaps.filter((g) => g.status === col.key);
          return (
            <div key={col.key} className="flex flex-col">
              <div className="mb-2 flex items-center justify-between px-1">
                <span className="text-sm font-semibold text-slate-700">{col.label}</span>
                <span className="rounded-full bg-slate-200 px-2 text-xs text-slate-600">
                  {items.length}
                </span>
              </div>
              <div className="flex flex-col gap-2">
                {items.map((g) => (
                  <div key={g.id} className="card p-3">
                    <div className="flex items-center justify-between">
                      <Badge className={SEVERITY_STYLES[g.severity]}>{g.severity}</Badge>
                      {g.due_date && (
                        <span className="text-[11px] text-[var(--muted)]">
                          due {new Date(g.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 text-sm text-slate-800">{g.description}</div>
                    {g.remediation_plan && (
                      <div className="mt-1 text-xs text-[var(--muted)]">
                        Plan: {g.remediation_plan}
                      </div>
                    )}
                    {g.owner && (
                      <div className="mt-1 text-[11px] text-[var(--muted)]">Owner: {g.owner}</div>
                    )}
                    <select
                      value={g.status}
                      onChange={(e) => move(g, e.target.value as GapStatus)}
                      className="mt-2 w-full rounded-md border border-[var(--border)] bg-white px-2 py-1 text-xs text-slate-600"
                    >
                      {GAP_COLUMNS.map((c) => (
                        <option key={c.key} value={c.key}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="rounded-lg border border-dashed border-[var(--border)] py-6 text-center text-xs text-[var(--muted)]">
                    Nothing here
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
