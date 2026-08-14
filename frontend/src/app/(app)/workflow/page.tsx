"use client";

/**
 * Workflow: the customer-facing replacement for the Knowledge Graph page.
 * One screen that shows the complete user flow of the system (monitor ->
 * obligations -> gaps -> tasks -> controls -> governance) with live counts,
 * plus an allocation workspace: every open task gets an owner and a due date
 * without leaving the page. Reads via the org-scoped Supabase client (RLS),
 * assignee roster via the worker's /org/roster.
 */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Radar,
  ShieldAlert,
  TriangleAlert,
  ListChecks,
  ShieldCheck,
  FileText,
  ChevronRight,
  UserRoundPlus,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getSupabase, workerFetch } from "@/lib/supabase";
import { TableSkeleton } from "@/components/Loading";
import { PageHeader, Badge, DemoBanner } from "@/components/ui";
import { toast } from "@/components/Toast";
import {
  PRIORITY_STYLES,
  TASK_COLUMNS,
  type Control,
  type Task,
  type TaskStatus,
} from "@/lib/types";

interface RosterRow {
  user_id: string;
  email: string | null;
  role: string;
}

const UNASSIGNED = "__unassigned__";

function isOpen(t: Task): boolean {
  return t.status !== "done";
}

function isOverdue(t: Task): boolean {
  if (!t.due_date || t.status === "done") return false;
  return new Date(t.due_date).getTime() < Date.now() - 24 * 3600 * 1000;
}

export default function WorkflowPage() {
  const [configured, setConfigured] = useState(true);
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [gapCounts, setGapCounts] = useState({ open: 0, urgent: 0 });
  const [controls, setControls] = useState<Control[]>([]);
  const [obligationCount, setObligationCount] = useState(0);
  const [alerts30d, setAlerts30d] = useState(0);
  const [policiesApproved, setPoliciesApproved] = useState(0);
  const [roster, setRoster] = useState<RosterRow[]>([]);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      setLoading(false);
      return;
    }
    const monthAgo = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString();
    // Counts come from exact count queries: PostgREST caps plain selects at
    // 1,000 rows, which silently understates gap numbers at this org's scale.
    Promise.all([
      supabase.from("tasks").select("*").order("created_at", { ascending: false }),
      supabase.from("gaps").select("id", { count: "exact", head: true }).in("status", ["open", "remediating"]),
      supabase
        .from("gaps")
        .select("id", { count: "exact", head: true })
        .in("status", ["open", "remediating"])
        .in("severity", ["critical", "high"]),
      supabase.from("controls").select("*"),
      supabase.from("obligations").select("id", { count: "exact", head: true }),
      supabase.from("alerts").select("id", { count: "exact", head: true }).gte("created_at", monthAgo),
      supabase.from("policies").select("id", { count: "exact", head: true }).eq("status", "approved"),
    ]).then(([t, gOpen, gUrgent, c, o, a, p]) => {
      setTasks((t.data as Task[]) ?? []);
      setGapCounts({ open: gOpen.count ?? 0, urgent: gUrgent.count ?? 0 });
      setControls((c.data as Control[]) ?? []);
      setObligationCount(o.count ?? 0);
      setAlerts30d(a.count ?? 0);
      setPoliciesApproved(p.count ?? 0);
      setLoading(false);
    });
    workerFetch("/org/roster")
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: RosterRow[]) => setRoster(Array.isArray(rows) ? rows : []))
      .catch(() => {});
  }, []);

  const openTasks = tasks.filter(isOpen);
  const unassigned = openTasks.filter((t) => !t.owner);
  const overdue = openTasks.filter(isOverdue);
  const effective = controls.filter((c) => c.effectiveness === "effective").length;
  const passRate = controls.length ? Math.round((effective / controls.length) * 100) : null;

  // Assignment options: everyone in the org, plus any names already on tasks
  // (e.g. suggested owners from mapping) so an existing value never disappears.
  const owners = useMemo(() => {
    const set = new Set<string>();
    roster.forEach((r) => r.email && set.add(r.email));
    tasks.forEach((t) => t.owner && set.add(t.owner));
    return Array.from(set).sort();
  }, [roster, tasks]);

  const workload = useMemo(() => {
    const counts = new Map<string, { open: number; overdue: number }>();
    openTasks.forEach((t) => {
      const key = t.owner || UNASSIGNED;
      const row = counts.get(key) ?? { open: 0, overdue: 0 };
      row.open += 1;
      if (isOverdue(t)) row.overdue += 1;
      counts.set(key, row);
    });
    // Members with zero open tasks still show up, so spare capacity is visible.
    roster.forEach((r) => {
      if (r.email && !counts.has(r.email)) counts.set(r.email, { open: 0, overdue: 0 });
    });
    return Array.from(counts.entries())
      .map(([owner, c]) => ({ owner, ...c }))
      .sort((a, b) => b.open - a.open || a.owner.localeCompare(b.owner));
  }, [openTasks, roster]);
  const maxLoad = Math.max(1, ...workload.map((w) => w.open));

  async function patchTask(task: Task, patch: Partial<Task>, label: string) {
    const prev = tasks;
    setTasks((cur) => cur.map((t) => (t.id === task.id ? { ...t, ...patch } : t)));
    const supabase = getSupabase();
    if (!supabase) return;
    const { error } = await supabase.from("tasks").update(patch).eq("id", task.id);
    if (error) {
      setTasks(prev);
      toast(`Couldn't update task: ${error.message}`, "error");
    } else {
      toast(label);
    }
  }

  const STAGES: {
    icon: LucideIcon;
    step: string;
    title: string;
    value: string;
    sub: string;
    href: string;
    alarm?: boolean;
  }[] = [
    {
      icon: Radar,
      step: "1 · MONITOR",
      title: "Horizon scanning",
      value: String(alerts30d),
      sub: "alerts in the last 30 days",
      href: "/dashboard",
    },
    {
      icon: ShieldAlert,
      step: "2 · STRUCTURE",
      title: "Obligations",
      value: String(obligationCount),
      sub: "extracted for your firm",
      href: "/obligations",
    },
    {
      icon: TriangleAlert,
      step: "3 · ASSESS",
      title: "Gap analysis",
      value: String(gapCounts.open),
      sub: `open · ${gapCounts.urgent} critical/high`,
      href: "/gaps",
      alarm: gapCounts.urgent > 0,
    },
    {
      icon: ListChecks,
      step: "4 · ACT",
      title: "Tasks",
      value: String(openTasks.length),
      sub: `open · ${unassigned.length} unassigned`,
      href: "/tasks",
      alarm: unassigned.length > 0,
    },
    {
      icon: ShieldCheck,
      step: "5 · PROVE",
      title: "Controls",
      value: passRate === null ? "n/a" : `${passRate}%`,
      sub: `effective of ${controls.length} controls`,
      href: "/controls",
    },
    {
      icon: FileText,
      step: "6 · GOVERN",
      title: "Policies",
      value: String(policiesApproved),
      sub: "approved and versioned",
      href: "/policies",
    },
  ];

  // The allocation queue: unassigned first, then overdue, then the rest of the
  // open tasks by priority.
  const PRIORITY_ORDER = { urgent: 0, high: 1, medium: 2, low: 3 } as const;
  const queue = [...openTasks].sort((a, b) => {
    const aU = a.owner ? 1 : 0;
    const bU = b.owner ? 1 : 0;
    if (aU !== bU) return aU - bU;
    const aO = isOverdue(a) ? 0 : 1;
    const bO = isOverdue(b) ? 0 : 1;
    if (aO !== bO) return aO - bO;
    return (PRIORITY_ORDER[a.priority] ?? 4) - (PRIORITY_ORDER[b.priority] ?? 4);
  });

  return (
    <div>
      <PageHeader
        title="Workflow"
        subtitle="The complete flow, from a circular landing to audit-ready proof, and who is doing what"
      />
      {!configured && <DemoBanner />}

      {loading ? (
        <TableSkeleton rows={8} />
      ) : (
        <div className="flex flex-col gap-6">
          {/* pipeline: the whole system as one flow */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {STAGES.map((s, i) => (
              <Link key={s.title} href={s.href} className="group relative">
                <div className="card flex h-full flex-col gap-1.5 p-4 transition-shadow hover:shadow-md">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold tracking-[.12em] text-[var(--brand)]">{s.step}</span>
                    <s.icon size={15} className="text-slate-400" />
                  </div>
                  <div className="text-sm font-semibold text-slate-800">{s.title}</div>
                  <div className="mt-auto">
                    <span className={`text-[22px] font-extrabold tracking-tight ${s.alarm ? "text-orange-600" : "text-slate-900"}`}>
                      {s.value}
                    </span>
                    <div className="text-[11px] leading-snug text-[var(--muted)]">{s.sub}</div>
                  </div>
                </div>
                {i < STAGES.length - 1 && (
                  <ChevronRight
                    size={14}
                    className="absolute -right-[9px] top-1/2 z-10 hidden -translate-y-1/2 text-slate-300 xl:block"
                  />
                )}
              </Link>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            {/* allocation queue */}
            <div className="card min-w-0 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <UserRoundPlus size={16} className="text-[var(--brand)]" />
                  <span className="text-sm font-semibold text-slate-800">Assign the work</span>
                </div>
                <span className="text-xs text-[var(--muted)]">
                  {unassigned.length} unassigned · {overdue.length} overdue
                </span>
              </div>
              {queue.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[var(--border)] py-10 text-center text-sm text-[var(--muted)]">
                  No open tasks. New obligations will generate work here automatically.
                </div>
              ) : (
                <div className="flex flex-col divide-y divide-[var(--border)]">
                  {queue.map((t) => (
                    <div key={t.id} className="flex flex-col gap-2 py-3 md:flex-row md:items-center md:gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-slate-800" title={t.title}>
                          {t.title}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2">
                          <Badge className={PRIORITY_STYLES[t.priority]}>{t.priority}</Badge>
                          {isOverdue(t) && <Badge className="bg-red-100 text-red-700">overdue</Badge>}
                          {!t.owner && <Badge className="bg-violet-100 text-violet-700">needs owner</Badge>}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <select
                          value={t.owner ?? UNASSIGNED}
                          onChange={(e) =>
                            patchTask(
                              t,
                              { owner: e.target.value === UNASSIGNED ? null : e.target.value },
                              e.target.value === UNASSIGNED ? "Owner cleared" : `Assigned to ${e.target.value}`,
                            )
                          }
                          className="w-[180px] rounded-md border border-[var(--border)] bg-white px-2 py-1 text-xs text-slate-700"
                        >
                          <option value={UNASSIGNED}>Unassigned</option>
                          {owners.map((o) => (
                            <option key={o} value={o}>
                              {o}
                            </option>
                          ))}
                        </select>
                        <input
                          type="date"
                          value={t.due_date ?? ""}
                          onChange={(e) =>
                            patchTask(t, { due_date: e.target.value || null }, e.target.value ? "Due date set" : "Due date cleared")
                          }
                          className="rounded-md border border-[var(--border)] bg-white px-2 py-1 text-xs text-slate-700"
                        />
                        <select
                          value={t.status}
                          onChange={(e) =>
                            patchTask(t, { status: e.target.value as TaskStatus }, `Moved to ${e.target.value.replace(/_/g, " ")}`)
                          }
                          className="rounded-md border border-[var(--border)] bg-white px-2 py-1 text-xs text-slate-700"
                        >
                          {TASK_COLUMNS.map((c) => (
                            <option key={c.key} value={c.key}>
                              {c.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* workload per person */}
            <div className="card h-fit p-4">
              <div className="mb-3 text-sm font-semibold text-slate-800">Team workload</div>
              {workload.length === 0 ? (
                <div className="text-sm text-[var(--muted)]">No open work.</div>
              ) : (
                <div className="flex flex-col gap-3">
                  {workload.map((w) => (
                    <div key={w.owner}>
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`truncate text-xs ${w.owner === UNASSIGNED ? "font-semibold text-violet-700" : "text-slate-700"}`}
                          title={w.owner === UNASSIGNED ? "Unassigned" : w.owner}
                        >
                          {w.owner === UNASSIGNED ? "Unassigned" : w.owner}
                        </span>
                        <span className="text-[11px] text-[var(--muted)]">
                          {w.open} open{w.overdue > 0 ? ` · ${w.overdue} overdue` : ""}
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className={`h-full rounded-full ${w.owner === UNASSIGNED ? "bg-violet-400" : w.overdue > 0 ? "bg-orange-400" : "bg-[var(--brand)]"}`}
                          style={{ width: `${(w.open / maxLoad) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-4 border-t border-[var(--border)] pt-3 text-[11px] leading-relaxed text-[var(--muted)]">
                Invite more teammates from the{" "}
                <Link href="/team" className="font-medium text-[var(--brand)] no-underline">
                  Team page
                </Link>
                . New members appear here as assignees right away.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
