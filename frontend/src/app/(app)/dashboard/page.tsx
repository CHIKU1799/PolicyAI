"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ShieldX,
  ShieldAlert,
  Clock,
  FileWarning,
  ArrowRight,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { getSupabase, workerFetch } from "@/lib/supabase";
import ScanButton from "@/components/ScanButton";
import { KpiSkeleton } from "@/components/Loading";
import type { Obligation, Gap, Control, Task, Alert, Severity } from "@/lib/types";

const SEV_COLOR: Record<Severity, string> = {
  critical: "#D14343",
  high: "#E0683C",
  medium: "#C77A1A",
  low: "#3E7CC0",
  informational: "#8A8D94",
};
const STATUS = [
  { key: "open", label: "Open", color: "#4B40C4" },
  { key: "in_review", label: "In review", color: "#C77A1A" },
  { key: "addressed", label: "Addressed", color: "#1F9D5B" },
  { key: "superseded", label: "Superseded", color: "#9A6BB8" },
  { key: "dismissed", label: "Dismissed", color: "#9A9DA4" },
];

interface ServerInsight {
  key: string;
  label: string;
  severity: string;
  count: number;
  action_href: string;
}
const SEV_TONE: Record<string, { sev: string; bg: string }> = {
  critical: { sev: "#C0392B", bg: "#FBEAE7" },
  high: { sev: "#B4541F", bg: "#FBEEE3" },
  medium: { sev: "#A6691B", bg: "#FBF1E2" },
  low: { sev: "#5B5E66", bg: "#EFEFEC" },
};

function spark(seed: number): string {
  const pts = Array.from({ length: 12 }, (_, i) => {
    const v = 17 + 9 * Math.sin(i * 0.7 + seed) + (i / 11) * 6;
    return `${(i / 11) * 120},${34 - v}`;
  });
  return pts.join(" ");
}

export default function DashboardPage() {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [controls, setControls] = useState<Control[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [covered, setCovered] = useState<Set<string>>(new Set());
  const [loadingData, setLoadingData] = useState(true);
  const [serverInsights, setServerInsights] = useState<ServerInsight[] | null>(null);
  const [reqCoverage, setReqCoverage] = useState<{ pct: number | null; covered: number; applicable: number } | null>(null);

  useEffect(() => {
    // Canonical, server-computed insights (richer than the client fallback below):
    // includes unmapped regulations, uncovered requirements, low-confidence mappings.
    workerFetch("/insights")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => {
        setServerInsights(d.insights ?? []);
        setReqCoverage(d.coverage ?? null);
      })
      .catch(() => setServerInsights(null));
  }, []);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;
    (async () => {
      const [o, g, c, t, a, oc] = await Promise.all([
        supabase.from("obligations").select("*"),
        supabase.from("gaps").select("*"),
        supabase.from("controls").select("*"),
        supabase.from("tasks").select("*"),
        supabase.from("alerts").select("*").order("created_at", { ascending: false }).limit(5),
        supabase.from("obligation_controls").select("obligation_id"),
      ]);
      setObligations((o.data as Obligation[]) ?? []);
      setGaps((g.data as Gap[]) ?? []);
      setControls((c.data as Control[]) ?? []);
      setTasks((t.data as Task[]) ?? []);
      setAlerts((a.data as Alert[]) ?? []);
      setCovered(new Set(((oc.data as { obligation_id: string }[]) ?? []).map((r) => r.obligation_id)));
      setLoadingData(false);
    })();
  }, []);

  const today = new Date().toISOString().slice(0, 10);
  const effectivePct = controls.length
    ? Math.round((controls.filter((c) => c.effectiveness === "effective").length / controls.length) * 100)
    : 0;
  const coveragePct = obligations.length
    ? Math.round((obligations.filter((o) => covered.has(o.id)).length / obligations.length) * 100)
    : 0;
  const openGaps = gaps.filter((g) => g.status === "open" || g.status === "remediating").length;
  const posture = Math.round(0.45 * effectivePct + 0.35 * coveragePct + 0.2 * (obligations.length ? 100 - Math.min(100, (openGaps / obligations.length) * 100) : 100)) || 0;

  const kpis = [
    { label: "Active obligations", value: obligations.filter((o) => o.status === "open").length, sub: "open & unaddressed", accent: "#4B40C4", seed: 1 },
    { label: "Open gaps", value: openGaps, sub: "needing remediation", accent: "#D14343", seed: 3 },
    { label: "Control effectiveness", value: `${effectivePct}%`, sub: "tested effective", accent: "#1F9D5B", seed: 2 },
    reqCoverage?.pct != null
      ? { label: "Requirement coverage", value: `${reqCoverage.pct}%`, sub: `${reqCoverage.covered.toLocaleString()} of ${reqCoverage.applicable.toLocaleString()} covered by policy`, accent: "#C77A1A", seed: 4 }
      : { label: "Coverage", value: `${coveragePct}%`, sub: "obligations with a control", accent: "#C77A1A", seed: 4 },
  ];

  const insights = [
    { label: "Overdue gaps", count: gaps.filter((g) => g.due_date && g.due_date < today && g.status !== "closed").length, icon: AlertTriangle, sev: "#C0392B", bg: "#FBEAE7", href: "/gaps" },
    { label: "Ineffective controls", count: controls.filter((c) => c.effectiveness === "ineffective").length, icon: ShieldX, sev: "#C0392B", bg: "#FBEAE7", href: "/controls" },
    { label: "Untested controls", count: controls.filter((c) => c.effectiveness === "untested").length, icon: ShieldAlert, sev: "#A6691B", bg: "#FBF1E2", href: "/controls" },
    { label: "Overdue tasks", count: tasks.filter((t) => t.due_date && t.due_date < today && t.status !== "done").length, icon: Clock, sev: "#A6691B", bg: "#FBF1E2", href: "/tasks" },
    { label: "Obligations with no control", count: obligations.filter((o) => o.status !== "dismissed" && !covered.has(o.id)).length, icon: FileWarning, sev: "#B4541F", bg: "#FBEEE3", href: "/obligations" },
  ].filter((i) => i.count > 0).sort((a, b) => b.count - a.count);

  // Prefer the canonical server insights; fall back to the client calc above.
  const priority =
    serverInsights !== null
      ? serverInsights.map((i) => ({
          label: i.label,
          count: i.count,
          href: i.action_href,
          ...(SEV_TONE[i.severity] ?? SEV_TONE.medium),
        }))
      : insights.map((i) => ({ label: i.label, count: i.count, href: i.href, sev: i.sev, bg: i.bg }));

  const sevCounts = (["critical", "high", "medium", "low", "informational"] as Severity[])
    .map((s) => ({ s, n: obligations.filter((o) => o.severity === s).length }))
    .filter((x) => x.n > 0);

  return (
    <div className="flex flex-col gap-4">
      {/* command band */}
      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        {/* posture gauge */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#23204A] to-[#15132E] p-5 text-white">
          <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(91,79,214,.45),transparent_70%)]" />
          <div className="text-[12px] font-semibold text-[#A8A4D6]">Compliance posture</div>
          <div className="mt-3.5 flex items-center gap-4">
            <svg width="104" height="104" viewBox="0 0 120 120" className="flex-none">
              <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,.12)" strokeWidth="11" />
              <circle
                cx="60" cy="60" r="50" fill="none" stroke="#34D399" strokeWidth="11" strokeLinecap="round"
                strokeDasharray="314.2" strokeDashoffset={314.2 * (1 - posture / 100)} transform="rotate(-90 60 60)"
                style={{ transition: "stroke-dashoffset 1s ease" }}
              />
              <text x="60" y="58" textAnchor="middle" fontSize="32" fontWeight="800" fill="#fff">{posture}</text>
              <text x="60" y="76" textAnchor="middle" fontSize="11" fontWeight="600" fill="#A8A4D6">/ 100</text>
            </svg>
            <div>
              <div className="inline-flex items-center gap-1.5 rounded-full bg-[rgba(52,211,153,.14)] px-2.5 py-1 text-[12px] font-bold text-[#34D399]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#34D399]" />
                {posture >= 75 ? "Strong" : posture >= 50 ? "Fair" : "At risk"}
              </div>
              <div className="mt-2.5 text-[12.5px] leading-relaxed text-[#C7C4E8]">
                {effectivePct}% controls effective · {coveragePct}% coverage
              </div>
            </div>
          </div>
          <div className="mt-4 flex gap-2 border-t border-white/10 pt-4">
            <Stat value={obligations.length} label="Obligations" />
            <Stat value={controls.length} label="Controls" />
            <Stat value={alerts.length >= 5 ? "5+" : alerts.length} label="Recent alerts" />
          </div>
        </div>

        {/* AI briefing */}
        <div className="card flex flex-col p-5">
          <div className="flex items-center gap-2.5">
            <span className="brand-grad flex h-6 w-6 items-center justify-center rounded-[7px]">
              <Sparkles size={13} className="text-white" />
            </span>
            <span className="text-[13px] font-bold tracking-tight">Executive briefing</span>
            <Link href="/ask" className="ml-auto flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--brand)]">
              Ask the Copilot <ArrowRight size={13} />
            </Link>
          </div>
          <div className="my-3 text-[13.5px] leading-relaxed text-[var(--text-2)]">
            Posture is <b className="text-[var(--text)]">{posture >= 75 ? "strong" : "developing"}</b> —{" "}
            <b className="text-[var(--text)]">{obligations.filter((o) => o.status === "open").length} active obligations</b>{" "}
            mapped, {openGaps} open {openGaps === 1 ? "gap" : "gaps"} to remediate, and{" "}
            {controls.filter((c) => c.effectiveness === "untested").length} controls still untested.
          </div>
          <div className="flex flex-col border-t border-[var(--hairline)]">
            {priority.slice(0, 4).map((p) => (
              <Link key={p.label} href={p.href} className="flex items-center gap-3 border-b border-[var(--hairline)] py-2.5 last:border-0">
                <span className="w-[58px] flex-none rounded-md px-2 py-1 text-center text-[10.5px] font-bold" style={{ color: p.sev, background: p.bg }}>
                  {p.count}
                </span>
                <span className="flex-1 text-[13px] leading-snug text-[#2A2D33]">{p.label}</span>
                <ChevronRight size={15} className="flex-none text-[#C0C0BA]" />
              </Link>
            ))}
            {priority.length === 0 && (
              <div className="py-3 text-[13px] text-[var(--muted)]">Nothing needs attention right now.</div>
            )}
          </div>
        </div>
      </div>

      {/* KPI row */}
      {loadingData ? (
        <KpiSkeleton />
      ) : (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="card overflow-hidden px-4 pt-4">
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-semibold text-[#8B8E95]">{k.label}</span>
            </div>
            <div className="mt-2 text-[30px] font-extrabold tracking-[-.025em] tabular-nums">{k.value}</div>
            <div className="mb-3 mt-0.5 text-[12px] text-[var(--muted-2)]">{k.sub}</div>
            <svg viewBox="0 0 120 34" preserveAspectRatio="none" className="-mx-4 block h-[30px] w-[calc(100%+32px)]">
              <polyline points={spark(k.seed)} fill="none" stroke={k.accent} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
            </svg>
          </div>
        ))}
      </div>
      )}

      {/* main grid */}
      <div className="grid items-start gap-4 lg:grid-cols-[1.55fr_1fr]">
        {/* horizon feed */}
        <div className="card">
          <div className="flex items-center justify-between border-b border-[var(--border-soft)] px-5 py-4">
            <div className="flex items-center gap-2.5">
              <span className="serif text-[15.5px] font-medium">Horizon — latest alerts</span>
              <span className="flex items-center gap-1.5 rounded-full bg-[#E6F4EC] px-2 py-0.5 text-[11px] font-semibold text-[var(--success)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" style={{ animation: "paiPulse 1.6s infinite" }} />
                Live
              </span>
            </div>
            <ScanButton />
          </div>
          <div>
            {alerts.length === 0 && (
              <div className="px-5 py-10 text-center text-[13px] text-[var(--muted)]">
                No alerts yet — run a scan to ingest the latest regulations.
              </div>
            )}
            {alerts.map((a) => (
              <div key={a.id} className="flex gap-3.5 border-b border-[var(--hairline)] px-5 py-3.5 last:border-0">
                <div className="mono flex h-[42px] w-[42px] flex-none items-center justify-center rounded-[10px] border border-[#EAEAE6] bg-[#F4F4F1] text-[10.5px] font-extrabold text-[var(--brand)]">
                  {a.kind === "new_obligation" ? "OBL" : a.message.match(/RBI|SEBI|IRDAI|MCA/)?.[0] ?? "REG"}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="mono text-[11.5px] text-[var(--muted-3)]">{a.kind.replace(/_/g, " ")}</span>
                    <span className="ml-auto text-[11.5px] text-[var(--muted-3)]">
                      {new Date(a.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-[13.5px] font-semibold leading-snug text-[#1F2127]">{a.message}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* right column */}
        <div className="flex flex-col gap-4">
          <div className="card p-5">
            <div className="serif mb-3.5 text-[15.5px] font-medium">Obligations by status</div>
            <div className="mb-3.5 flex h-2.5 overflow-hidden rounded-md">
              {STATUS.map((s) => {
                const n = obligations.filter((o) => o.status === s.key).length;
                const pct = obligations.length ? (n / obligations.length) * 100 : 0;
                return pct > 0 ? <div key={s.key} style={{ width: `${pct}%`, background: s.color }} /> : null;
              })}
            </div>
            {STATUS.map((s) => (
              <div key={s.key} className="flex items-center gap-2.5 py-1">
                <span className="h-2.5 w-2.5 flex-none rounded-[3px]" style={{ background: s.color }} />
                <span className="flex-1 text-[13px] text-[var(--text-2)]">{s.label}</span>
                <span className="text-[13px] font-bold tabular-nums">{obligations.filter((o) => o.status === s.key).length}</span>
              </div>
            ))}
          </div>

          <div className="card p-5">
            <div className="serif mb-3.5 text-[15.5px] font-medium">Obligations by severity</div>
            {sevCounts.length === 0 && <div className="text-[13px] text-[var(--muted)]">No obligations yet.</div>}
            {sevCounts.map(({ s, n }) => {
              const pct = obligations.length ? (n / obligations.length) * 100 : 0;
              return (
                <div key={s} className="mb-3 last:mb-0">
                  <div className="mb-1.5 flex justify-between">
                    <span className="text-[12.5px] font-medium capitalize text-[var(--text-2)]">{s}</span>
                    <span className="text-[12.5px] font-bold tabular-nums" style={{ color: SEV_COLOR[s] }}>{n}</span>
                  </div>
                  <div className="h-[7px] overflow-hidden rounded-md bg-[var(--border-soft)]">
                    <div className="h-full rounded-md" style={{ width: `${pct}%`, background: SEV_COLOR[s] }} />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card p-5">
            <div className="serif mb-1 text-[15.5px] font-medium">Recently superseded</div>
            <div className="mb-3.5 text-[12px] text-[var(--muted-2)]">
              Obligations retired when their source regulation was replaced.
            </div>
            {(() => {
              const gone = obligations
                .filter((o) => o.status === "superseded")
                .sort((a, b) => (b.invalidated_at ?? "").localeCompare(a.invalidated_at ?? ""))
                .slice(0, 5);
              if (gone.length === 0)
                return (
                  <div className="text-[13px] text-[var(--muted)]">
                    Nothing superseded yet — everything mapped is currently in force.
                  </div>
                );
              return gone.map((o) => (
                <div
                  key={o.id}
                  className="flex items-start gap-2.5 border-b border-[var(--hairline)] py-2 last:border-0"
                >
                  <span className="mt-0.5 h-2 w-2 flex-none rounded-full bg-[#9A6BB8]" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-[#2A2D33] line-through decoration-1">
                      {o.title}
                    </div>
                    {(o.valid_to || o.invalidated_at) && (
                      <div className="text-[11.5px] text-[var(--muted-3)]">
                        retired{" "}
                        {new Date(o.valid_to ?? o.invalidated_at!).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              ));
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div className="flex-1">
      <div className="text-[18px] font-extrabold">{value}</div>
      <div className="mt-px text-[10.5px] text-[#9D99CC]">{label}</div>
    </div>
  );
}
