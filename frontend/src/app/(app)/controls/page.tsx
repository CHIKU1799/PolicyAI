"use client";

import { useEffect, useState } from "react";
import { getSupabase } from "@/lib/supabase";
import { PageHeader, Kpi, Badge, DemoBanner, EmptyState } from "@/components/ui";
import { EFFECTIVENESS_STYLES, type Control, type ControlTest } from "@/lib/types";

const RESULT_STYLES: Record<string, string> = {
  pass: "bg-emerald-100 text-emerald-700",
  fail: "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
};

export default function ControlsPage() {
  const [configured, setConfigured] = useState(true);
  const [controls, setControls] = useState<Control[]>([]);
  const [tests, setTests] = useState<ControlTest[]>([]);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    supabase
      .from("controls")
      .select("*")
      .order("ref_code", { ascending: true })
      .then(({ data }) => setControls((data as Control[]) ?? []));
    supabase
      .from("control_tests")
      .select("*")
      .order("performed_at", { ascending: false })
      .then(({ data }) => setTests((data as ControlTest[]) ?? []));
  }, []);

  const count = (e: string) => controls.filter((c) => c.effectiveness === e).length;
  const latestTest = (controlId: string) => tests.find((t) => t.control_id === controlId);

  return (
    <div>
      <PageHeader
        title="Controls Testing & Monitoring"
        subtitle="Real-time control effectiveness across your compliance obligations"
      />
      {!configured && <DemoBanner />}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Effective" value={count("effective")} tone="ok" />
        <Kpi label="Partial" value={count("partial")} tone="warn" />
        <Kpi label="Ineffective" value={count("ineffective")} tone="danger" />
        <Kpi label="Untested" value={count("untested")} hint="Need a first test" />
      </div>

      {controls.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No controls yet"
            body="Define the controls that satisfy your obligations, then record tests to track effectiveness here."
          />
        </div>
      ) : (
        <div className="card mt-6 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Control</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3">Frequency</th>
                <th className="px-4 py-3">Effectiveness</th>
                <th className="px-4 py-3">Latest test</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {controls.map((c) => {
                const t = latestTest(c.id);
                return (
                  <tr key={c.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">
                        {c.ref_code ? `${c.ref_code} · ` : ""}
                        {c.title}
                      </div>
                      {c.description && (
                        <div className="line-clamp-1 text-xs text-[var(--muted)]">
                          {c.description}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 capitalize text-[var(--muted)]">{c.control_type}</td>
                    <td className="px-4 py-3 text-[var(--muted)]">{c.owner ?? "—"}</td>
                    <td className="px-4 py-3 text-[var(--muted)]">{c.frequency ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Badge className={EFFECTIVENESS_STYLES[c.effectiveness]}>
                        {c.effectiveness}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {t && t.result ? (
                        <div className="flex items-center gap-2">
                          <Badge className={RESULT_STYLES[t.result] ?? "bg-slate-100"}>
                            {t.result}
                          </Badge>
                          <span className="text-[11px] text-[var(--muted)]">
                            {t.performed_at
                              ? new Date(t.performed_at).toLocaleDateString()
                              : ""}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-[var(--muted)]">no tests</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
