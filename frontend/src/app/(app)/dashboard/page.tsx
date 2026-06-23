"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from "recharts";
import { getSupabase } from "@/lib/supabase";
import { PageHeader, Kpi, DemoBanner, Badge } from "@/components/ui";
import ScanButton from "@/components/ScanButton";
import { SEVERITY_STYLES, type Obligation, type Severity } from "@/lib/types";

interface Stats {
  obligations: number;
  openTasks: number;
  scans24h: number;
  newRegs7d: number;
}

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "informational"];
const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#0284c7",
  informational: "#64748b",
};

export default function DashboardPage() {
  const [configured, setConfigured] = useState(true);
  const [stats, setStats] = useState<Stats>({ obligations: 0, openTasks: 0, scans24h: 0, newRegs7d: 0 });
  const [bySeverity, setBySeverity] = useState<{ severity: Severity; count: number }[]>([]);
  const [recent, setRecent] = useState<Obligation[]>([]);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      return;
    }
    (async () => {
      const since24 = new Date(Date.now() - 86400_000).toISOString();
      const since7d = new Date(Date.now() - 7 * 86400_000).toISOString();

      const [obl, tasks, scans, regs, obls] = await Promise.all([
        supabase.from("obligations").select("id", { count: "exact", head: true }).eq("status", "open"),
        supabase.from("tasks").select("id", { count: "exact", head: true }).neq("status", "done"),
        supabase.from("scan_runs").select("id", { count: "exact", head: true }).gte("started_at", since24),
        supabase.from("alerts").select("id", { count: "exact", head: true }).eq("kind", "new_regulation").gte("created_at", since7d),
        supabase.from("obligations").select("*").order("created_at", { ascending: false }).limit(60),
      ]);

      setStats({
        obligations: obl.count ?? 0,
        openTasks: tasks.count ?? 0,
        scans24h: scans.count ?? 0,
        newRegs7d: regs.count ?? 0,
      });

      const all = (obls.data as Obligation[]) ?? [];
      setRecent(all.slice(0, 6));
      const counts = SEVERITY_ORDER.map((severity) => ({
        severity,
        count: all.filter((o) => o.severity === severity).length,
      }));
      setBySeverity(counts);
    })();
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <PageHeader
          title="Compliance Dashboard"
          subtitle="Live posture across continuously monitored Indian regulators"
        />
        <ScanButton />
      </div>
      {!configured && <DemoBanner />}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Active obligations" value={stats.obligations} tone={stats.obligations ? "danger" : "default"} hint="Open and unaddressed" />
        <Kpi label="Open tasks" value={stats.openTasks} tone="warn" hint="Across all obligations" />
        <Kpi label="Scans (24h)" value={stats.scans24h} tone="ok" hint="Monitoring agent runs" />
        <Kpi label="New regulations (7d)" value={stats.newRegs7d} hint="Detected this week" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-1">
          <div className="mb-4 text-sm font-semibold">Obligations by severity</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={bySeverity}>
              <XAxis dataKey="severity" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} width={24} />
              <Tooltip cursor={{ fill: "#f1f5f9" }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {bySeverity.map((d) => (
                  <Cell key={d.severity} fill={SEVERITY_COLOR[d.severity]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 text-sm font-semibold">Recent obligations</div>
          {recent.length === 0 ? (
            <div className="py-10 text-center text-sm text-[var(--muted)]">
              No obligations yet. They appear as the monitoring agent maps new regulations to your knowledge base.
            </div>
          ) : (
            <ul className="divide-y divide-[var(--border)]">
              {recent.map((o) => (
                <li key={o.id} className="flex items-start justify-between gap-4 py-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{o.title}</div>
                    <div className="mt-0.5 line-clamp-1 text-xs text-[var(--muted)]">{o.summary}</div>
                  </div>
                  <Badge className={SEVERITY_STYLES[o.severity]}>{o.severity}</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
