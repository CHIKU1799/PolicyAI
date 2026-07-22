"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getSupabase } from "@/lib/supabase";
import { PageHeader, Kpi, Badge, DemoBanner, EmptyState } from "@/components/ui";
import { KpiSkeleton, TableSkeleton } from "@/components/Loading";
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
  const [loading, setLoading] = useState(true);

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
      .then(({ data }) => {
        setControls((data as Control[]) ?? []);
        setLoading(false);
      });
    supabase
      .from("control_tests")
      .select("*")
      .order("performed_at", { ascending: false })
      .then(({ data }) => setTests((data as ControlTest[]) ?? []));
  }, []);

  const count = (e: string) => controls.filter((c) => c.effectiveness === e).length;
  const latestTest = (controlId: string) => tests.find((t) => t.control_id === controlId);

  // Pass-rate per ISO week over the last 12 weeks, from the test history.
  const trend = useMemo(() => {
    const now = Date.now();
    const week = 7 * 24 * 3600 * 1000;
    const buckets: { label: string; pass: number; total: number }[] = [];
    for (let i = 11; i >= 0; i--) {
      const start = new Date(now - (i + 1) * week);
      buckets.push({
        label: start.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        pass: 0,
        total: 0,
      });
    }
    for (const t of tests) {
      if (!t.performed_at || !t.result) continue;
      const age = now - new Date(t.performed_at).getTime();
      const idx = 11 - Math.floor(age / week);
      if (idx < 0 || idx > 11) continue;
      buckets[idx].total += 1;
      if (t.result === "pass") buckets[idx].pass += 1;
    }
    return buckets.map((b) => ({
      label: b.label,
      tests: b.total,
      passRate: b.total ? Math.round((100 * b.pass) / b.total) : null,
    }));
  }, [tests]);
  const testedWeeks = trend.filter((b) => b.tests > 0).length;

  return (
    <div>
      <PageHeader
        title="Controls Testing & Monitoring"
        subtitle="Real-time control effectiveness across your compliance obligations"
      />
      {!configured && <DemoBanner />}

      <div className="card mb-4 border-[#E4E0F7] bg-gradient-to-b from-[#F8F7FE] to-white p-4">
        <div className="text-sm font-semibold text-[var(--brand-ink)]">What is a control?</div>
        <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-slate-600">
          A control is a check or process your team runs to make sure a regulatory obligation is
          actually being met, for example a maker-checker review before payouts, or a quarterly KYC
          file audit. Each control is tested on a schedule; the test result (pass, partial or fail)
          drives its effectiveness rating below and your overall compliance score.
        </p>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-slate-500">
          <span><b className="text-slate-700">1. Define</b> a control for an obligation</span>
          <span><b className="text-slate-700">2. Test</b> it at its set frequency</span>
          <span><b className="text-slate-700">3. Record</b> the result to update effectiveness</span>
        </div>
      </div>

      {loading ? (
        <>
          <KpiSkeleton />
          <div className="mt-6">
            <TableSkeleton />
          </div>
        </>
      ) : (
        <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Effective" value={count("effective")} tone="ok" hint="Latest test passed; working as intended" />
        <Kpi label="Partial" value={count("partial")} tone="warn" hint="Works, but with gaps to close" />
        <Kpi label="Ineffective" value={count("ineffective")} tone="danger" hint="Latest test failed; needs remediation" />
        <Kpi label="Untested" value={count("untested")} hint="No test recorded yet; run a first test" />
      </div>

      {testedWeeks >= 2 && (
        <div className="card mt-4 p-4">
          <div className="mb-1 text-sm font-semibold text-slate-700">
            Test pass rate, last 12 weeks
          </div>
          <div className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#EEF0F4" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "#71757E" }}
                  tickLine={false}
                  axisLine={{ stroke: "#E2E5EB" }}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 50, 100]}
                  tick={{ fontSize: 11, fill: "#71757E" }}
                  tickLine={false}
                  axisLine={false}
                  unit="%"
                />
                <Tooltip
                  formatter={(v: number, _n, item) => [
                    `${v}% pass (${item?.payload?.tests} test${item?.payload?.tests === 1 ? "" : "s"})`,
                    "",
                  ]}
                  separator=""
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E2E5EB" }}
                />
                <Line
                  type="monotone"
                  dataKey="passRate"
                  stroke="#4B40C4"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#4B40C4", strokeWidth: 0 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {controls.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No controls yet"
            body="Start from the Obligations page: pick an obligation, define the control (the check or process) that satisfies it, then record test results here to track whether it works."
          />
        </div>
      ) : (
        <div className="card mt-6 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Control</th>
                <th className="px-4 py-3" title="Preventive stops issues before they happen; detective finds them after">Type</th>
                <th className="px-4 py-3" title="Person responsible for running and testing this control">Owner</th>
                <th className="px-4 py-3" title="How often this control should be tested">Test frequency</th>
                <th className="px-4 py-3" title="Rating from the most recent test result">Effectiveness</th>
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
                    <td className="px-4 py-3 text-[var(--muted)]">{c.owner ?? "Unassigned"}</td>
                    <td className="px-4 py-3 text-[var(--muted)]">{c.frequency ?? "Not set"}</td>
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
                        <span className="text-xs text-[var(--muted)]">Not tested yet</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
        </>
      )}
    </div>
  );
}
