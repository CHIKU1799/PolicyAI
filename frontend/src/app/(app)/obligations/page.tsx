"use client";

import { Fragment, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  FileText,
  ListChecks,
  History,
  ArrowRight,
} from "lucide-react";
import { getSupabase, workerFetch } from "@/lib/supabase";
import { TableSkeleton } from "@/components/Loading";
import { PageHeader, Badge, DemoBanner, EmptyState, ExportButton } from "@/components/ui";
import { toast } from "@/components/Toast";
import { downloadCSV } from "@/lib/export";
import {
  SEVERITY_STYLES,
  EFFECTIVENESS_STYLES,
  POLICY_STATUS_STYLES,
  type Obligation,
} from "@/lib/types";

const STATUS_TONE: Record<string, string> = {
  in_review: "bg-amber-100 text-amber-700",
  addressed: "bg-emerald-100 text-emerald-700",
  dismissed: "bg-slate-200 text-slate-500",
  superseded: "bg-slate-200 text-slate-600 line-through decoration-1",
};

interface LinkedControl {
  obligation_id: string;
  controls: { ref_code: string | null; title: string; effectiveness: string } | null;
}
interface LinkedPolicy {
  obligation_id: string;
  policies: { title: string; status: string } | null;
}
interface LinkedTask {
  obligation_id: string;
  title: string;
  status: string;
}

export default function ObligationsPage() {
  const [configured, setConfigured] = useState(true);
  const [rows, setRows] = useState<Obligation[]>([]);
  const [loadingRows, setLoadingRows] = useState(true);
  const [controls, setControls] = useState<LinkedControl[]>([]);
  const [policies, setPolicies] = useState<LinkedPolicy[]>([]);
  const [tasks, setTasks] = useState<LinkedTask[]>([]);
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
      .then(({ data }) => {
        setRows((data as Obligation[]) ?? []);
        setLoadingRows(false);
      });
    supabase
      .from("obligation_controls")
      .select("obligation_id, controls(ref_code,title,effectiveness)")
      .then(({ data }) => setControls((data as unknown as LinkedControl[]) ?? []));
    supabase
      .from("obligation_policies")
      .select("obligation_id, policies(title,status)")
      .then(({ data }) => setPolicies((data as unknown as LinkedPolicy[]) ?? []));
    supabase
      .from("tasks")
      .select("obligation_id, title, status")
      .then(({ data }) => setTasks((data as LinkedTask[]) ?? []));
  }, []);

  async function setStatus(o: Obligation, status: string) {
    const prevStatus = o.status;
    setRows((prev) => prev.map((r) => (r.id === o.id ? { ...r, status } : r)));
    const supabase = getSupabase();
    if (!supabase) return;
    const { error } = await supabase.from("obligations").update({ status }).eq("id", o.id);
    if (error) {
      setRows((prev) => prev.map((r) => (r.id === o.id ? { ...r, status: prevStatus } : r)));
      toast(`Couldn't update status: ${error.message}`, "error");
    } else {
      toast(`Obligation marked ${status.replace(/_/g, " ")}`);
    }
  }

  const filtered = severity === "all" ? rows : rows.filter((r) => r.severity === severity);

  return (
    <div>
      <PageHeader
        title="Obligations"
        subtitle="Structured obligations mapped to your controls, policies, and tasks"
      />
      {!configured && <DemoBanner />}

      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex gap-2">
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
        <ExportButton
          label="Export register"
          onClick={() =>
            downloadCSV(
              "obligations-register.csv",
              filtered.map((o) => ({
                title: o.title,
                severity: o.severity,
                status: o.status,
                detected: o.created_at,
                summary: o.summary,
                what_changed: o.what_changed,
                gap_analysis: o.gap_analysis,
              })),
            )
          }
        />
      </div>

      {loadingRows ? (
        <TableSkeleton rows={8} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No obligations to show"
          body="As the monitoring agent maps new regulations to your profile, obligations land here with their controls, policies, gaps, and tasks."
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border)] bg-slate-50 text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="w-8 px-4 py-3"></th>
                <th className="px-4 py-3">Obligation</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Mapped to</th>
                <th className="px-4 py-3">Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filtered.map((o) => {
                const oc = controls.filter((c) => c.obligation_id === o.id);
                const op = policies.filter((p) => p.obligation_id === o.id);
                const ot = tasks.filter((t) => t.obligation_id === o.id);
                return (
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
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge className={SEVERITY_STYLES[o.severity]}>{o.severity}</Badge>
                          {STATUS_TONE[o.status] && (
                            <Badge className={STATUS_TONE[o.status]}>
                              {o.status.replace(/_/g, " ")}
                            </Badge>
                          )}
                          {o.mapping_confidence != null && o.mapping_confidence < 0.5 && (
                            <Badge className="bg-amber-100 text-amber-700">review</Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-[var(--muted)]">
                        <span className="inline-flex items-center gap-1">
                          <ShieldCheck size={13} />
                          {oc.length}
                        </span>{" "}
                        <span className="inline-flex items-center gap-1">
                          <FileText size={13} />
                          {op.length}
                        </span>{" "}
                        <span className="inline-flex items-center gap-1">
                          <ListChecks size={13} />
                          {ot.length}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[var(--muted)]">
                        {new Date(o.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                    {open === o.id && (
                      <tr className="bg-slate-50/60">
                        <td></td>
                        <td colSpan={4} className="px-4 py-4">
                          <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-[var(--border)] pb-3">
                            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                              Status
                            </span>
                            <Badge className="bg-slate-100 capitalize text-slate-700">
                              {o.status.replace(/_/g, " ")}
                            </Badge>
                            <span className="mx-1 text-[var(--border)]">|</span>
                            {o.status !== "in_review" && o.status !== "superseded" && (
                              <TriageButton onClick={() => setStatus(o, "in_review")}>
                                Mark in review
                              </TriageButton>
                            )}
                            {o.status !== "addressed" && o.status !== "superseded" && (
                              <TriageButton tone="ok" onClick={() => setStatus(o, "addressed")}>
                                Mark addressed
                              </TriageButton>
                            )}
                            {o.status !== "dismissed" && o.status !== "superseded" && (
                              <TriageButton tone="muted" onClick={() => setStatus(o, "dismissed")}>
                                Dismiss
                              </TriageButton>
                            )}
                            {(o.status === "addressed" || o.status === "dismissed") && (
                              <TriageButton onClick={() => setStatus(o, "open")}>Reopen</TriageButton>
                            )}
                          </div>
                          <Detail label="Summary" value={o.summary} />
                          <Detail label="Why this applies to you" value={o.relevance_rationale} />

                          <div className="mb-3 flex flex-wrap gap-2">
                            {o.obligation_type && <MetaChip label="Type" value={o.obligation_type} />}
                            {o.frequency && <MetaChip label="Frequency" value={o.frequency} />}
                            {o.regulatory_citation && (
                              <MetaChip label="Citation" value={o.regulatory_citation} />
                            )}
                            {o.effective_date && (
                              <MetaChip label="Effective" value={o.effective_date} />
                            )}
                            {o.mapping_confidence != null && (
                              <MetaChip
                                label="Confidence"
                                value={`${Math.round(o.mapping_confidence * 100)}%`}
                              />
                            )}
                          </div>

                          <Detail label="What changed" value={o.what_changed} />
                          <Detail label="Gap analysis" value={o.gap_analysis} />
                          <Detail label="Penalty for non-compliance" value={o.penalty_summary} />
                          <Detail label="Evidence required" value={o.evidence_required} />

                          <div className="mt-4 grid gap-4 sm:grid-cols-3">
                            <MapBlock title="Controls" icon={<ShieldCheck size={13} />}>
                              {oc.length === 0 && <None />}
                              {oc.map(
                                (c, i) =>
                                  c.controls && (
                                    <div key={i} className="flex items-center justify-between gap-2">
                                      <span className="text-slate-700">
                                        {c.controls.ref_code ? `${c.controls.ref_code} · ` : ""}
                                        {c.controls.title}
                                      </span>
                                      <Badge
                                        className={
                                          EFFECTIVENESS_STYLES[
                                            c.controls
                                              .effectiveness as keyof typeof EFFECTIVENESS_STYLES
                                          ] ?? "bg-slate-100"
                                        }
                                      >
                                        {c.controls.effectiveness}
                                      </Badge>
                                    </div>
                                  ),
                              )}
                            </MapBlock>
                            <MapBlock title="Policies" icon={<FileText size={13} />}>
                              {op.length === 0 && <None />}
                              {op.map(
                                (p, i) =>
                                  p.policies && (
                                    <div key={i} className="flex items-center justify-between gap-2">
                                      <span className="text-slate-700">{p.policies.title}</span>
                                      <Badge
                                        className={
                                          POLICY_STATUS_STYLES[
                                            p.policies.status as keyof typeof POLICY_STATUS_STYLES
                                          ] ?? "bg-slate-100"
                                        }
                                      >
                                        {p.policies.status.replace("_", " ")}
                                      </Badge>
                                    </div>
                                  ),
                              )}
                            </MapBlock>
                            <MapBlock title="Tasks" icon={<ListChecks size={13} />}>
                              {ot.length === 0 && <None />}
                              {ot.map((t, i) => (
                                <div key={i} className="flex items-center justify-between gap-2">
                                  <span className="text-slate-700">{t.title}</span>
                                  <span className="text-[11px] capitalize text-[var(--muted)]">
                                    {t.status.replace("_", " ")}
                                  </span>
                                </div>
                              ))}
                            </MapBlock>
                          </div>

                          {open === o.id && <ObligationTimeline regulationNodeId={o.regulation_node_id} />}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
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

function MapBlock({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-white p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        {icon}
        {title}
      </div>
      <div className="space-y-1.5 text-sm">{children}</div>
    </div>
  );
}

function None() {
  return <span className="text-xs text-[var(--muted)]">None mapped</span>;
}

function TriageButton({
  children,
  onClick,
  tone = "default",
}: {
  children: React.ReactNode;
  onClick: () => void;
  tone?: "default" | "ok" | "muted";
}) {
  const cls = {
    default: "border-[var(--border)] text-slate-700 hover:border-[#4b40c4] hover:text-[#4b40c4]",
    ok: "border-emerald-200 text-emerald-700 hover:bg-emerald-50",
    muted: "border-[var(--border)] text-[var(--muted)] hover:bg-slate-50",
  }[tone];
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`rounded-md border bg-white px-2.5 py-1 text-xs font-medium transition-colors ${cls}`}
    >
      {children}
    </button>
  );
}

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-white px-2 py-1 text-xs">
      <span className="font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</span>
      <span className="capitalize text-slate-700">{value.replace(/_/g, " ")}</span>
    </span>
  );
}

interface TimelineNode {
  id: string;
  title: string | null;
  is_current: boolean;
  effective_from: string | null;
  effective_to: string | null;
}
interface TimelineEvent {
  action: string;
  entity_type: string;
  detail: Record<string, unknown>;
  created_at: string;
}
interface TimelineRequirement {
  text: string;
  requirement_type: string;
  frequency: string | null;
  citation: string | null;
  evidence_expected: string | null;
  penalty: string | null;
  gap_status: string | null;
  gap_description: string | null;
}
interface TimelineData {
  chain: TimelineNode[];
  events: TimelineEvent[];
  requirements: TimelineRequirement[];
}

// Lazy-loads the bitemporal lineage for an obligation's source regulation: the
// supersession chain (what replaced what, and when) plus the append-only audit log.
function ObligationTimeline({ regulationNodeId }: { regulationNodeId: string | null }) {
  const [data, setData] = useState<TimelineData | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    if (!regulationNodeId) {
      setState("error");
      return;
    }
    let alive = true;
    workerFetch(`/timeline/${regulationNodeId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: TimelineData) => alive && (setData(d), setState("ready")))
      .catch(() => alive && setState("error"));
    return () => {
      alive = false;
    };
  }, [regulationNodeId]);

  const hasHistory =
    data && (data.chain.length > 1 || data.events.length > 0);
  const reqs = data?.requirements ?? [];

  return (
    <div className="mt-4 space-y-4">
      {state === "ready" && reqs.length > 0 && (
        <div className="rounded-lg border border-[var(--border)] bg-white p-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            <ListChecks size={13} /> Requirements from this regulation ({reqs.length})
          </div>
          <ul className="space-y-2">
            {reqs.map((r, i) => (
              <li key={i} className="border-b border-[var(--border)] pb-2 text-sm last:border-0 last:pb-0">
                <div className="flex items-start gap-2">
                  <Badge className="mt-0.5 bg-slate-100 text-slate-600">
                    {r.requirement_type.replace(/_/g, " ")}
                  </Badge>
                  <span className="flex-1 text-slate-700">{r.text}</span>
                  <Badge
                    className={
                      r.gap_status
                        ? "mt-0.5 bg-red-100 text-red-700"
                        : "mt-0.5 bg-emerald-100 text-emerald-700"
                    }
                  >
                    {r.gap_status ? "gap" : "covered"}
                  </Badge>
                </div>
                {r.gap_description && (
                  <div className="mt-1 pl-1 text-[12px] text-red-700">{r.gap_description}</div>
                )}
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 pl-1 text-[11px] text-[var(--muted)]">
                  {r.frequency && <span>cadence: {r.frequency.replace(/_/g, " ")}</span>}
                  {r.citation && <span>cite: {r.citation}</span>}
                  {r.evidence_expected && <span>evidence: {r.evidence_expected}</span>}
                  {r.penalty && <span className="text-red-600">penalty: {r.penalty}</span>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-lg border border-[var(--border)] bg-white p-3">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          <History size={13} /> History &amp; timeline
        </div>
        {state === "loading" && (
          <div className="text-xs text-[var(--muted)]">Loading lineage…</div>
        )}
        {state === "error" && (
          <div className="text-xs text-[var(--muted)]">Timeline unavailable.</div>
        )}
        {state === "ready" && !hasHistory && (
          <div className="text-xs text-[var(--muted)]">
            In force since first recorded — no supersessions yet.
          </div>
        )}
        {state === "ready" && hasHistory && (
          <div className="space-y-3">
            {data!.chain.length > 1 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {data!.chain.map((n, i) => (
                <Fragment key={n.id}>
                  <span
                    className={`rounded-md px-2 py-1 ${
                      n.is_current
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-500 line-through decoration-1"
                    }`}
                    title={n.effective_from ? `from ${n.effective_from}` : undefined}
                  >
                    {n.title ?? "regulation"}
                  </span>
                  {i < data!.chain.length - 1 && (
                    <ArrowRight size={12} className="text-[var(--muted)]" />
                  )}
                </Fragment>
              ))}
            </div>
          )}
          {data!.events.length > 0 && (
            <ul className="space-y-1.5 border-t border-[var(--border)] pt-2">
              {data!.events.map((e, i) => (
                <li key={i} className="flex items-baseline gap-2 text-xs">
                  <span className="font-mono text-[11px] text-[var(--muted)]">
                    {new Date(e.created_at).toLocaleDateString()}
                  </span>
                  <span className="text-slate-700">{e.action.replace(/_/g, " ")}</span>
                </li>
              ))}
            </ul>
          )}
          </div>
        )}
      </div>
    </div>
  );
}
