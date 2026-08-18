"use client";

/** Rows for the "Latest regulatory activity" panel. Each alert is a clickable
 *  row routed by its kind, with a regulator chip, a cleaned two-line title,
 *  and a meta line carrying the event type, severity pill, and relative time. */

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { Alert, Severity } from "@/lib/types";
import { Shimmer } from "@/components/Loading";

const SEV_PILL: Record<Severity, { fg: string; bg: string }> = {
  critical: { fg: "#B42318", bg: "#FEECEA" },
  high: { fg: "#B54708", bg: "#FDF1E2" },
  medium: { fg: "#8A6116", bg: "#FBF6EA" },
  low: { fg: "#175CD3", bg: "#EAF1FD" },
  informational: { fg: "#5B5E66", bg: "#F0F0EC" },
};

/** Regulator chip palette: RBI indigo, SEBI blue, IRDAI teal, MCA slate,
 *  PIB amber; every other known source falls back to gray. */
const REG_STYLE: Record<string, { fg: string; bg: string }> = {
  RBI: { fg: "#4B40C4", bg: "#EEECFA" },
  SEBI: { fg: "#1E5EF6", bg: "#E8EFFD" },
  IRDAI: { fg: "#0F766E", bg: "#E4F4F2" },
  MCA: { fg: "#475569", bg: "#EEF1F5" },
  PIB: { fg: "#B4661F", bg: "#FDF3E6" },
};
const GRAY = { fg: "#71757E", bg: "#F0F0EC" };

const SOURCE_RE = /\b(RBI|SEBI|IRDAI|MCA|PIB|PFRDA|IFSCA|NPCI|FIU|MEITY|CERT-IN|DGFT)\b/i;
const SEV_RE = /\s*\((critical|high|medium|low|informational)\)/i;
// Boilerplate prefixes the ingest pipeline puts on messages; the chip and the
// kind label already say this, so the title drops it.
const PREFIX_RE =
  /^new\s+(?:RBI|SEBI|IRDAI|MCA|PIB|PFRDA|IFSCA|NPCI|FIU|MEITY|CERT-IN|DGFT)?\s*(?:regulation|obligation|circular|advisory)\s*:\s*/i;

/** Where a click should land, by alert kind. */
const KIND_ROUTE: Record<string, { href: string; label: string }> = {
  new_regulation: { href: "/obligations", label: "New regulation" },
  new_obligation: { href: "/obligations", label: "New obligation" },
  deadline_approaching: { href: "/tasks", label: "Deadline approaching" },
  regulation_superseded: { href: "/obligations", label: "Superseded" },
  policy_conflict: { href: "/gaps", label: "Policy conflict" },
  control_failed: { href: "/controls", label: "Control failed" },
  scan_failed: { href: "/knowledge-base", label: "Scan issue" },
};

function parse(a: Alert) {
  const src = a.message.match(SOURCE_RE);
  const code = src ? src[1].toUpperCase() : a.kind === "new_obligation" ? "OBL" : "REG";
  const sevMatch = a.message.match(SEV_RE);
  const sev = sevMatch ? (sevMatch[1].toLowerCase() as Severity) : null;
  let title = a.message.replace(PREFIX_RE, "").replace(SEV_RE, "").trim();
  // Scan-failure alerts embed the raw fetch error after the first colon;
  // keep only the human-readable "Scan failed for <source>" part here.
  if (a.kind === "scan_failed") title = title.split(/:\s/)[0];
  const route = KIND_ROUTE[a.kind] ?? { href: "/obligations", label: "Update" };
  return { code, chip: REG_STYLE[code] ?? GRAY, sev, title, route };
}

function relTime(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export default function ActivityFeed({ alerts, loading }: { alerts: Alert[]; loading: boolean }) {
  if (loading) {
    return (
      <div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-start gap-3 border-b border-[var(--hairline)] px-5 py-3.5 last:border-0">
            <Shimmer className="mt-0.5 h-5 w-[46px] flex-none" />
            <div className="flex flex-1 flex-col gap-1.5">
              <Shimmer className="h-3.5 w-4/5" />
              <Shimmer className="h-2.5 w-2/5" />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (alerts.length === 0) {
    return (
      <div className="px-5 py-10 text-center text-[13px] text-[var(--muted)]">
        No alerts yet, run a scan to ingest the latest regulations.
      </div>
    );
  }
  return (
    <div>
      {alerts.map((a) => {
        const p = parse(a);
        return (
          <Link
            key={a.id}
            href={p.route.href}
            className="group flex items-start gap-3 border-b border-[var(--hairline)] px-5 py-3 no-underline transition-colors last:border-0 hover:bg-[#FAFAF8]"
          >
            <span
              className="mono mt-0.5 w-[46px] flex-none rounded-md px-1 py-1 text-center text-[10px] font-bold leading-none"
              style={{ color: p.chip.fg, background: p.chip.bg }}
            >
              {p.code}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[12.5px] font-medium leading-snug text-[#26282e] group-hover:text-[#15161B]">
                {p.title}
              </span>
              <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <span className="text-[10.5px] font-semibold uppercase tracking-[.06em] text-[#9a9da4]">
                  {p.route.label}
                </span>
                {p.sev && (
                  <span
                    className="rounded-full px-1.5 py-px text-[10px] font-bold capitalize leading-[14px]"
                    style={{ color: SEV_PILL[p.sev].fg, background: SEV_PILL[p.sev].bg }}
                  >
                    {p.sev}
                  </span>
                )}
                <span className="text-[10.5px] text-[#b3b6bc]">{relTime(a.created_at)}</span>
              </span>
            </span>
            <ChevronRight
              size={14}
              className="mt-1 flex-none text-[#d5d7db] transition-transform group-hover:translate-x-0.5 group-hover:text-[#9a9da4]"
            />
          </Link>
        );
      })}
    </div>
  );
}
