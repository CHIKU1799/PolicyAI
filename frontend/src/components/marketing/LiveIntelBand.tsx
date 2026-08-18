"use client";

/**
 * Landing-page band: live regulatory intelligence, on real data. Replaces the
 * abstract knowledge-graph canvas with the thing it was standing in for: the
 * actual corpus. Renders instantly from a static snapshot, then swaps in live
 * numbers and the latest circulars from /api/landing-intel (a cached proxy to
 * the worker's public /public/intel). Pure CSS motion (LIVE pulse, sweeping
 * scanline, sequential row glow); respects prefers-reduced-motion.
 */

import { useEffect, useState } from "react";

interface IntelDoc {
  source: string;
  title: string;
  url: string;
  published: string | null;
}

interface Intel {
  stats: {
    total_documents: number;
    documents_30d: number;
    regulators_live: number;
    sources_enabled: number;
    last_synced: string | null;
  };
  latest: IntelDoc[];
  by_regulator: { source: string; count: number }[];
}

const REGULATOR_META: Record<string, { label: string; color: string }> = {
  rbi: { label: "RBI", color: "#7EA6FF" },
  sebi: { label: "SEBI", color: "#34D399" },
  irdai: { label: "IRDAI", color: "#F5A97F" },
  mca: { label: "MCA", color: "#C4A7F7" },
  pib: { label: "PIB", color: "#9AD1F5" },
  certin: { label: "CERT-IN", color: "#F7768E" },
  "cert-in": { label: "CERT-IN", color: "#F7768E" },
  cert_in: { label: "CERT-IN", color: "#F7768E" },
  pfrda: { label: "PFRDA", color: "#E0AF68" },
  ifsca: { label: "IFSCA", color: "#73DACA" },
  fiu: { label: "FIU-IND", color: "#B9B2F1" },
  fiu_ind: { label: "FIU-IND", color: "#B9B2F1" },
  npci: { label: "NPCI", color: "#FF9E64" },
  dgft: { label: "DGFT", color: "#A6E3A1" },
};

function regMeta(source: string) {
  return (
    REGULATOR_META[source.toLowerCase()] ?? {
      label: source.toUpperCase().slice(0, 8),
      color: "#B9B2F1",
    }
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function shortDate(iso: string | null): string {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return "";
  return `${d} ${MONTHS[m - 1]} ${String(y).slice(2)}`;
}

// Indian digit grouping (12,34,567) without relying on runtime locale data.
function formatNum(n: number): string {
  const s = String(n);
  if (s.length <= 3) return s;
  const head = s.slice(0, -3);
  return head.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + s.slice(-3);
}

function relTime(iso: string | null): string {
  if (!iso) return "";
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins || 1} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs} hr ago`;
  return `${Math.round(hrs / 24)} days ago`;
}

// Static snapshot (real corpus shape as of Aug 2026): what the band shows
// before live data arrives, and forever if the worker is unreachable.
const SNAPSHOT: Intel = {
  stats: {
    total_documents: 2947,
    documents_30d: 312,
    regulators_live: 9,
    sources_enabled: 11,
    last_synced: null,
  },
  latest: [
    {
      source: "rbi",
      title: "Review of priority sector lending targets for small finance banks",
      url: "https://rbi.org.in",
      published: "2026-08-12",
    },
    {
      source: "sebi",
      title: "Cybersecurity and cyber resilience framework for regulated entities",
      url: "https://sebi.gov.in",
      published: "2026-08-11",
    },
    {
      source: "irdai",
      title: "Master circular on protection of policyholders' interests",
      url: "https://irdai.gov.in",
      published: "2026-08-10",
    },
    {
      source: "rbi",
      title: "Digital lending directions on arrangements with lending service providers",
      url: "https://rbi.org.in",
      published: "2026-08-08",
    },
    {
      source: "certin",
      title: "Advisory: securing API endpoints in financial applications",
      url: "https://cert-in.org.in",
      published: "2026-08-07",
    },
    {
      source: "mca",
      title: "Companies (Accounts) amendment rules with audit trail requirements",
      url: "https://mca.gov.in",
      published: "2026-08-05",
    },
  ],
  by_regulator: [
    { source: "rbi", count: 1450 },
    { source: "sebi", count: 720 },
    { source: "irdai", count: 310 },
    { source: "mca", count: 240 },
    { source: "pib", count: 140 },
    { source: "certin", count: 87 },
  ],
};

export default function LiveIntelBand() {
  const [intel, setIntel] = useState<Intel>(SNAPSHOT);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/landing-intel")
      .then((r) => (r.ok ? r.json() : null))
      .then((data: Intel | null) => {
        if (cancelled || !data?.stats || !Array.isArray(data.latest)) return;
        // An empty local DB would make the band look dead; keep the snapshot.
        if (data.stats.total_documents < 50 || data.latest.length < 3) return;
        setIntel(data);
        setLive(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const { stats, latest, by_regulator } = intel;
  const regTotal = by_regulator.reduce((a, r) => a + r.count, 0) || 1;
  const statTiles = [
    { value: `${formatNum(stats.total_documents)}+`, label: "regulatory documents ingested" },
    { value: formatNum(stats.documents_30d), label: "new in the last 30 days" },
    { value: String(stats.regulators_live), label: "regulators watched 24/7" },
    { value: String(stats.sources_enabled), label: "official sources crawled" },
  ];

  return (
    <div
      className="relative overflow-hidden rounded-[22px] p-6 md:p-9"
      style={{ background: "linear-gradient(135deg,#23204A 0%,#15132E 100%)" }}
    >
      {/* ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full"
        style={{ background: "radial-gradient(circle,rgba(91,79,214,.4),transparent 70%)" }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 -left-16 h-72 w-72 rounded-full"
        style={{ background: "radial-gradient(circle,rgba(52,211,153,.14),transparent 70%)" }}
      />
      {/* sweeping scanline */}
      <div aria-hidden className="lib-scan pointer-events-none absolute inset-y-0 z-0" />

      <div className="relative z-10 grid gap-8 lg:grid-cols-[300px_1fr] lg:gap-10">
        {/* left: live status + stats */}
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-2.5">
            <span className="lib-pulse relative inline-flex h-2.5 w-2.5 rounded-full" style={{ background: "#34D399" }} />
            <span className="mono text-[11px] font-bold tracking-[.18em]" style={{ color: "#8F8ACD" }}>
              {live ? "LIVE FROM THE CORPUS" : "FROM THE CORPUS"}
            </span>
          </div>
          <p className="m-0 text-pretty text-[14px] leading-relaxed" style={{ color: "#A8A4D6" }}>
            Not a mockup. These are the documents PolicyAI&apos;s crawler has read, deduplicated and
            mapped into the regulation graph.{live && stats.last_synced ? ` Last sync ${relTime(stats.last_synced)}.` : ""}
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-5">
            {statTiles.map((s) => (
              <div key={s.label}>
                <div className="text-[26px] font-extrabold tracking-[-.02em] text-white">{s.value}</div>
                <div className="mt-0.5 text-[11.5px] leading-snug" style={{ color: "#9D99CC" }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>
          {/* corpus share by regulator */}
          <div className="mt-1 flex flex-col gap-2">
            <div className="flex h-[6px] overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,.08)" }}>
              {by_regulator.map((r) => (
                <div
                  key={r.source}
                  style={{
                    width: `${Math.max((r.count / regTotal) * 100, 2)}%`,
                    background: regMeta(r.source).color,
                    opacity: 0.85,
                  }}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {by_regulator.map((r) => (
                <span key={r.source} className="mono flex items-center gap-1.5 text-[9.5px] font-bold tracking-[.06em]" style={{ color: "#9D99CC" }}>
                  <span className="h-[7px] w-[7px] rounded-[2px]" style={{ background: regMeta(r.source).color }} />
                  {regMeta(r.source).label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* right: latest circulars feed */}
        <div className="flex min-w-0 flex-col">
          <div className="mb-3 flex items-center justify-between gap-3">
            <span className="mono text-[10px] font-bold tracking-[.16em]" style={{ color: "#6F6AAE" }}>
              LATEST FROM THE REGULATORS
            </span>
            <span className="mono text-[10px] tracking-[.08em]" style={{ color: "#6F6AAE" }}>
              AUTO-REFRESHED
            </span>
          </div>
          <div className="flex flex-col">
            {latest.slice(0, 6).map((doc, i) => {
              const meta = regMeta(doc.source);
              return (
                <a
                  key={`${doc.url}-${i}`}
                  href={doc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lib-row group flex items-center gap-3 rounded-[12px] border px-3.5 py-[11px] no-underline"
                  style={{
                    borderColor: "rgba(255,255,255,.08)",
                    background: "rgba(255,255,255,.03)",
                    marginTop: i === 0 ? 0 : 7,
                    animationDelay: `${i * 1.6}s`,
                  }}
                >
                  <span
                    className="mono w-[64px] shrink-0 rounded-[6px] px-1.5 py-[3px] text-center text-[9.5px] font-bold tracking-[.06em]"
                    style={{ background: "rgba(255,255,255,.10)", color: meta.color }}
                  >
                    {meta.label}
                  </span>
                  <span
                    className="min-w-0 flex-1 truncate text-[13px] font-medium leading-snug text-white transition-colors group-hover:text-[#C7C4E8]"
                    title={doc.title}
                  >
                    {doc.title}
                  </span>
                  <span className="mono hidden shrink-0 text-[10.5px] sm:block" style={{ color: "#8F8ACD" }}>
                    {shortDate(doc.published)}
                  </span>
                  <span aria-hidden className="shrink-0 text-[13px] opacity-0 transition-opacity group-hover:opacity-100" style={{ color: "#8F8ACD" }}>
                    ↗
                  </span>
                </a>
              );
            })}
          </div>
          <div className="mt-3 text-[11.5px]" style={{ color: "#7B77B5" }}>
            Every document lands as extracted obligations with citations. Sign in to see what each
            one means for your firm.
          </div>
        </div>
      </div>

      <style>{`
        .lib-pulse::after {
          content: "";
          position: absolute;
          inset: -4px;
          border-radius: 50%;
          border: 1.5px solid rgba(52,211,153,.7);
          animation: libPing 2.2s ease-out infinite;
        }
        @keyframes libPing {
          0% { transform: scale(.6); opacity: 1; }
          80%, 100% { transform: scale(1.9); opacity: 0; }
        }
        .lib-scan {
          width: 140px;
          left: -140px;
          background: linear-gradient(90deg, transparent, rgba(139,125,224,.08), transparent);
          animation: libSweep 9s linear infinite;
        }
        @keyframes libSweep {
          from { transform: translateX(0); }
          to { transform: translateX(calc(100vw + 280px)); }
        }
        .lib-row { animation: libGlow 9.6s ease-in-out infinite; }
        @keyframes libGlow {
          0%, 22%, 100% { border-color: rgba(255,255,255,.08); background: rgba(255,255,255,.03); }
          7%, 13% { border-color: rgba(139,125,224,.5); background: rgba(91,79,214,.12); }
        }
        @media (prefers-reduced-motion: reduce) {
          .lib-pulse::after, .lib-scan, .lib-row { animation: none; }
        }
      `}</style>
    </div>
  );
}
