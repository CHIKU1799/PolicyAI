"use client";

// Posture improvement: answers "are we better off than before?" using only
// fields that actually exist under RLS: gaps (created_at, status, severity,
// coverage_status, requirement_id, invalidated_at), obligations (created_at,
// invalidated_at), obligation_controls (created_at), company_documents
// (uploaded_at). The reference point is the previous policy upload when one
// exists, otherwise 30 days ago.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowRight,
  FileUp,
  Flag,
  Minus,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { getSupabase } from "@/lib/supabase";

// Series colors validated for CVD separation against the app's light surface:
// indigo (resolved, the brand accent) vs amber (still open, needs attention).
const COLOR_RESOLVED = "#4B40C4";
const COLOR_OPEN = "#C77A1A";

const OPEN_STATUSES = new Set(["open", "remediating"]);
const RESOLVED_STATUSES = new Set(["closed", "accepted"]);

interface GapRow {
  id: string;
  requirement_id: string | null;
  severity: string;
  status: string;
  coverage_status: string | null;
  created_at: string;
  invalidated_at: string | null;
}
interface DocRow {
  id: string;
  filename: string;
  status: string;
  uploaded_at: string;
}
interface OblRow {
  id: string;
  status: string;
  created_at: string;
  invalidated_at: string | null;
}
interface LinkRow {
  obligation_id: string;
  created_at: string;
}

const ms = (iso: string | null | undefined) => (iso ? Date.parse(iso) : NaN);

function isResolved(g: GapRow): boolean {
  return RESOLVED_STATUSES.has(g.status) || g.invalidated_at != null;
}

/** Coverage (obligations with at least one linked control) as of time t. */
function coverageAt(obls: OblRow[], links: LinkRow[], t: number) {
  const firstLink = new Map<string, number>();
  for (const l of links) {
    const at = ms(l.created_at);
    const prev = firstLink.get(l.obligation_id);
    if (prev === undefined || at < prev) firstLink.set(l.obligation_id, at);
  }
  let total = 0;
  let covered = 0;
  for (const o of obls) {
    if (ms(o.created_at) > t) continue;
    const gone = ms(o.invalidated_at);
    if (!Number.isNaN(gone) && gone <= t) continue;
    total += 1;
    const linkAt = firstLink.get(o.id);
    if (linkAt !== undefined && linkAt <= t) covered += 1;
  }
  return { total, covered, pct: total ? Math.round((covered / total) * 100) : null };
}

export default function PostureImprovement() {
  const [gaps, setGaps] = useState<GapRow[]>([]);
  const [docs, setDocs] = useState<DocRow[]>([]);
  const [obls, setObls] = useState<OblRow[]>([]);
  const [links, setLinks] = useState<LinkRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState(true);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setConfigured(false);
      setLoading(false);
      return;
    }
    (async () => {
      const [g, d, o, oc] = await Promise.all([
        supabase
          .from("gaps")
          .select("id, requirement_id, severity, status, coverage_status, created_at, invalidated_at"),
        supabase
          .from("company_documents")
          .select("id, filename, status, uploaded_at")
          .order("uploaded_at", { ascending: false }),
        supabase.from("obligations").select("id, status, created_at, invalidated_at"),
        supabase.from("obligation_controls").select("obligation_id, created_at"),
      ]);
      setGaps((g.data as GapRow[]) ?? []);
      setDocs((d.data as DocRow[]) ?? []);
      setObls((o.data as OblRow[]) ?? []);
      setLinks((oc.data as LinkRow[]) ?? []);
      setLoading(false);
    })();
  }, []);

  const now = Date.now();
  const prevDoc = docs.length >= 2 ? docs[1] : null;
  const latestDoc = docs.length >= 1 ? docs[0] : null;
  const refTime = prevDoc ? ms(prevDoc.uploaded_at) : now - 30 * 24 * 3600 * 1000;
  const refLabel = prevDoc
    ? `since previous upload (${new Date(refTime).toLocaleDateString()})`
    : "vs 30 days ago";

  // Delta tiles ------------------------------------------------------------
  const covNow = useMemo(() => coverageAt(obls, links, now), [obls, links, now]);
  const covRef = useMemo(() => coverageAt(obls, links, refTime), [obls, links, refTime]);
  const covDelta =
    covNow.pct !== null && covRef.pct !== null ? covNow.pct - covRef.pct : null;

  const resolvedTotal = gaps.filter(isResolved).length;
  const resolvedOfRef = gaps.filter((g) => ms(g.created_at) <= refTime && isResolved(g)).length;
  const onFileAtRef = gaps.filter((g) => ms(g.created_at) <= refTime).length;
  const newSinceRef = gaps.filter((g) => ms(g.created_at) > refTime);
  const newStillOpen = newSinceRef.filter((g) => OPEN_STATUSES.has(g.status) && !g.invalidated_at).length;
  const openHighNow = gaps.filter(
    (g) =>
      OPEN_STATUSES.has(g.status) &&
      !g.invalidated_at &&
      (g.severity === "critical" || g.severity === "high"),
  ).length;

  // Trend: of the gaps recorded up to each week, how many are resolved today
  // vs still open. Both series are exact; resolution dates are not stored, so
  // the split reflects current status, stated in the caption.
  const trend = useMemo(() => {
    if (gaps.length === 0) return [];
    const earliest = Math.min(...gaps.map((g) => ms(g.created_at)));
    const start = Math.min(earliest, now - 84 * 24 * 3600 * 1000);
    const buckets = 12;
    const step = Math.max((now - start) / buckets, 24 * 3600 * 1000);
    const out: { label: string; open: number; resolved: number }[] = [];
    for (let i = 1; i <= buckets; i++) {
      const t = start + i * step;
      const recorded = gaps.filter((g) => ms(g.created_at) <= t);
      const resolved = recorded.filter(isResolved).length;
      out.push({
        label: new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        open: recorded.length - resolved,
        resolved,
      });
    }
    return out;
  }, [gaps, now]);

  // Per-document comparison: requirement-level findings recorded in each
  // document's mapping window (its upload until the next upload). Earlier
  // findings are dropped and rebuilt on re-map, so an empty previous window
  // means that version was fully re-assessed.
  const docWindows = useMemo(() => {
    if (!prevDoc || !latestDoc) return null;
    const split = ms(latestDoc.uploaded_at);
    const inWindow = (g: GapRow, from: number, to: number) => {
      const at = ms(g.created_at);
      return g.requirement_id !== null && at >= from && at < to;
    };
    const breakdown = (rows: GapRow[]) => ({
      total: rows.length,
      partial: rows.filter((g) => g.coverage_status === "partial").length,
      missing: rows.filter((g) => g.coverage_status === "missing").length,
      conflicting: rows.filter((g) => g.coverage_status === "conflicting").length,
    });
    return {
      prev: breakdown(gaps.filter((g) => inWindow(g, ms(prevDoc.uploaded_at), split))),
      latest: breakdown(gaps.filter((g) => inWindow(g, split, Infinity))),
    };
  }, [gaps, prevDoc, latestDoc]);

  if (!configured) return null;

  if (loading) {
    return (
      <div className="card p-5">
        <div className="h-4 w-44 animate-pulse rounded bg-[var(--border-soft)]" />
        <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-[var(--border-soft)]" />
          ))}
        </div>
      </div>
    );
  }

  // Nothing to measure yet.
  if (gaps.length === 0 && docs.length === 0) {
    return (
      <div className="card p-5">
        <Header />
        <div className="mt-3 flex flex-col items-start gap-2 rounded-xl border border-dashed border-[var(--border-soft)] bg-[#FAFAF8] p-5">
          <div className="text-[13.5px] font-semibold text-[#2A2D33]">No posture history yet</div>
          <p className="max-w-xl text-[13px] leading-relaxed text-[var(--muted)]">
            Upload your first policy document so the mapping engine can record a coverage
            baseline. Every later upload is then compared against it.
          </p>
          <Link
            href="/knowledge-base"
            className="mt-1 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--brand)]"
          >
            <FileUp size={13} /> Upload a policy <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <Header />

      {/* single upload: baseline recorded, no comparison possible yet */}
      {docs.length === 1 && (
        <div className="mt-3 flex items-start gap-2.5 rounded-xl bg-[#F4F3FC] px-4 py-3">
          <Flag size={15} className="mt-0.5 flex-none text-[var(--brand)]" />
          <div className="text-[12.5px] leading-relaxed text-[#3A3D45]">
            <b>Baseline recorded</b> from {latestDoc!.filename} on{" "}
            {new Date(latestDoc!.uploaded_at).toLocaleDateString()}. Upload your next policy
            version to see improvement against this baseline.
          </div>
        </div>
      )}

      {/* delta tiles */}
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <DeltaTile
          label="Control coverage"
          value={covNow.pct !== null ? `${covNow.pct}%` : "n/a"}
          sub={`${covNow.covered} of ${covNow.total} obligations`}
          delta={covDelta}
          deltaLabel={covDelta !== null ? `${covDelta > 0 ? "+" : ""}${covDelta} pts ${refLabel}` : undefined}
          goodWhen="up"
        />
        <DeltaTile
          label="Gaps resolved"
          value={resolvedTotal}
          sub={`of ${gaps.length} recorded in total`}
          delta={onFileAtRef > 0 ? resolvedOfRef : null}
          deltaLabel={
            onFileAtRef > 0
              ? `${resolvedOfRef} of ${onFileAtRef} on file at reference now resolved`
              : undefined
          }
          goodWhen="up"
        />
        <DeltaTile
          label="New gaps"
          value={newSinceRef.length}
          sub={refLabel}
          delta={newStillOpen > 0 ? -newStillOpen : 0}
          deltaLabel={newStillOpen > 0 ? `${newStillOpen} still open` : "all resolved already"}
          goodWhen="up"
        />
        <DeltaTile
          label="Open high severity"
          value={openHighNow}
          sub="critical and high gaps open now"
          delta={openHighNow > 0 ? -openHighNow : 0}
          deltaLabel={openHighNow > 0 ? "needs remediation first" : "none outstanding"}
          goodWhen="up"
        />
      </div>

      {/* trend chart */}
      {gaps.length > 0 && trend.length > 0 && (
        <div className="mt-5">
          <div className="mb-0.5 text-[13px] font-semibold text-[#3A3D45]">
            Gap resolution over time
          </div>
          <div className="mb-2 text-[11.5px] text-[var(--muted-2)]">
            Of the gaps recorded up to each week: resolved to date vs still open.
          </div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend} margin={{ top: 4, right: 8, bottom: 0, left: -22 }}>
                <CartesianGrid stroke="#EEF0F4" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "#71757E" }}
                  tickLine={false}
                  axisLine={{ stroke: "#E2E5EB" }}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: "#71757E" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E2E5EB" }}
                />
                <Legend
                  iconType="plainline"
                  wrapperStyle={{ fontSize: 12, color: "#3A3D45" }}
                />
                <Area
                  type="monotone"
                  dataKey="resolved"
                  name="Resolved"
                  stackId="1"
                  stroke={COLOR_RESOLVED}
                  strokeWidth={2}
                  fill={COLOR_RESOLVED}
                  fillOpacity={0.14}
                />
                <Area
                  type="monotone"
                  dataKey="open"
                  name="Still open"
                  stackId="1"
                  stroke={COLOR_OPEN}
                  strokeWidth={2}
                  fill={COLOR_OPEN}
                  fillOpacity={0.14}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* per-document comparison strip */}
      {docWindows && prevDoc && latestDoc && (
        <div className="mt-5">
          <div className="mb-2 text-[13px] font-semibold text-[#3A3D45]">
            Previous vs current policy version
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-stretch">
            <DocCard
              title="Previous"
              doc={prevDoc}
              counts={docWindows.prev}
              emptyNote="Findings from this version were re-assessed in the latest mapping run."
            />
            <div className="hidden items-center sm:flex">
              <ArrowRight size={16} className="text-[#C0C0BA]" />
            </div>
            <DocCard title="Current" doc={latestDoc} counts={docWindows.latest} highlight />
          </div>
          <div className="mt-2 text-[11.5px] text-[var(--muted-2)]">
            Counts are requirement-level findings recorded after each upload. Covered
            requirements are not stored as gaps, so fewer findings means better coverage.
          </div>
        </div>
      )}
    </div>
  );
}

function Header() {
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="serif text-[15.5px] font-medium">Posture improvement</div>
        <div className="mt-0.5 text-[12px] text-[var(--muted-2)]">
          Are you better off than before? Progress since your previous policy version.
        </div>
      </div>
      <Link
        href="/gaps"
        className="hidden items-center gap-1.5 text-[12.5px] font-semibold text-[var(--brand)] sm:flex"
      >
        Work the gaps <ArrowRight size={13} />
      </Link>
    </div>
  );
}

function DeltaTile({
  label,
  value,
  sub,
  delta,
  deltaLabel,
  goodWhen,
}: {
  label: string;
  value: React.ReactNode;
  sub: string;
  delta: number | null;
  deltaLabel?: string;
  goodWhen: "up" | "down";
}) {
  let tone = "#8B8E95";
  let Icon = Minus;
  if (delta !== null && delta !== 0) {
    const good = goodWhen === "up" ? delta > 0 : delta < 0;
    tone = good ? "#1F9D5B" : "#D14343";
    Icon = delta > 0 ? TrendingUp : TrendingDown;
  }
  return (
    <div className="rounded-xl border border-[var(--border-soft)] bg-[#FBFBF9] px-4 py-3">
      <div className="text-[12px] font-semibold text-[#8B8E95]">{label}</div>
      <div className="mt-1 text-[24px] font-extrabold tracking-[-.02em] tabular-nums">{value}</div>
      <div className="text-[11.5px] text-[var(--muted-2)]">{sub}</div>
      {deltaLabel && (
        <div className="mt-1.5 flex items-center gap-1.5 text-[11.5px] font-semibold" style={{ color: tone }}>
          <Icon size={13} className="flex-none" />
          <span className="leading-snug">{deltaLabel}</span>
        </div>
      )}
    </div>
  );
}

function DocCard({
  title,
  doc,
  counts,
  highlight,
  emptyNote,
}: {
  title: string;
  doc: { filename: string; uploaded_at: string };
  counts: { total: number; partial: number; missing: number; conflicting: number };
  highlight?: boolean;
  emptyNote?: string;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
        highlight ? "border-[#D9D5F5] bg-[#F8F7FE]" : "border-[var(--border-soft)] bg-[#FBFBF9]"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-bold uppercase tracking-wide text-[#8B8E95]">{title}</span>
        <span className="ml-auto text-[11px] text-[var(--muted-3)]">
          {new Date(doc.uploaded_at).toLocaleDateString()}
        </span>
      </div>
      <div className="mt-1 truncate text-[13px] font-semibold text-[#2A2D33]" title={doc.filename}>
        {doc.filename}
      </div>
      {counts.total === 0 && emptyNote ? (
        <div className="mt-2 text-[11.5px] leading-relaxed text-[var(--muted-2)]">{emptyNote}</div>
      ) : (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] tabular-nums">
          <span className="text-[#A6691B]">
            <b>{counts.partial}</b> partial
          </span>
          <span className="text-[#C0392B]">
            <b>{counts.missing}</b> missing
          </span>
          <span className="text-[#8E2B85]">
            <b>{counts.conflicting}</b> conflicting
          </span>
          <span className="text-[var(--muted-2)]">
            <b>{counts.total}</b> findings
          </span>
        </div>
      )}
    </div>
  );
}
