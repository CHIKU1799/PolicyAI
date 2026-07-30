"use client";

/** Rows for the "Latest regulatory activity" panel. Each alert gets a compact
 *  regulator chip (derived from the message source token), a one-line title,
 *  a severity dot when the alert message carries one, and a relative time. */

import type { Alert, Severity } from "@/lib/types";
import { Shimmer } from "@/components/Loading";

const SEV_DOT: Record<Severity, string> = {
  critical: "#D14343",
  high: "#E0683C",
  medium: "#C77A1A",
  low: "#3E7CC0",
  informational: "#8A8D94",
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

const SOURCE_RE = /\b(RBI|SEBI|IRDAI|MCA|PIB|PFRDA|IFSCA|NPCI|FIU|MEITY)\b/i;
const SEV_RE = /\((critical|high|medium|low|informational)\)/i;

function regulatorOf(a: Alert): { code: string; fg: string; bg: string } {
  const m = a.message.match(SOURCE_RE);
  const code = m ? m[1].toUpperCase() : a.kind === "new_obligation" ? "OBL" : "REG";
  return { code, ...(REG_STYLE[code] ?? GRAY) };
}

function severityOf(a: Alert): Severity | null {
  const m = a.message.match(SEV_RE);
  return m ? (m[1].toLowerCase() as Severity) : null;
}

function relTime(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export default function ActivityFeed({ alerts, loading }: { alerts: Alert[]; loading: boolean }) {
  if (loading) {
    return (
      <div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 border-b border-[var(--hairline)] px-5 py-[13px] last:border-0">
            <Shimmer className="h-5 w-[46px] flex-none" />
            <Shimmer className="h-3.5 flex-1" />
            <Shimmer className="h-3 w-8 flex-none" />
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
        const reg = regulatorOf(a);
        const sev = severityOf(a);
        return (
          <div key={a.id} className="flex items-center gap-3 border-b border-[var(--hairline)] px-5 py-[11px] last:border-0">
            <span
              className="mono w-[46px] flex-none rounded-md px-1 py-1 text-center text-[10px] font-bold leading-none"
              style={{ color: reg.fg, background: reg.bg }}
            >
              {reg.code}
            </span>
            <span className="min-w-0 flex-1 truncate text-[12.5px] text-[#3a3d44]" title={a.message}>
              {a.message}
            </span>
            {sev && (
              <span
                className="h-2 w-2 flex-none rounded-full"
                title={sev}
                style={{ background: SEV_DOT[sev] }}
              />
            )}
            <span className="mono w-10 flex-none text-right text-[10px] text-[#9a9da4]">
              {relTime(a.created_at)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
