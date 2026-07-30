"use client";

/** Mock-styled KPI stat card: small label, big numeric, optional colored
 *  delta chip, muted hint line. Delta chips are only rendered when the
 *  caller could compute a real delta, never faked. */

export type DeltaTone = "positive" | "negative" | "warn" | "neutral";

export interface StatDelta {
  text: string;
  tone: DeltaTone;
}

const TONE: Record<DeltaTone, { fg: string; bg: string }> = {
  positive: { fg: "#1F9D5B", bg: "#E6F4EC" },
  negative: { fg: "#C0392B", bg: "#FDECEC" },
  warn: { fg: "#B4661F", bg: "#FFF3E6" },
  neutral: { fg: "#54565E", bg: "#EEF1F5" },
};

export default function StatCard({
  label,
  value,
  hint,
  delta,
}: {
  label: string;
  value: React.ReactNode;
  hint: string;
  delta?: StatDelta;
}) {
  return (
    <div className="card p-4 shadow-[0_1px_2px_rgba(17,18,27,.04)]">
      <div className="text-[11.5px] font-semibold text-[#71757e]">{label}</div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-[28px] font-bold leading-none tracking-[-.02em] tabular-nums">{value}</span>
        {delta && (
          <span
            className="rounded-md px-1.5 py-0.5 text-[10.5px] font-bold leading-none"
            style={{ color: TONE[delta.tone].fg, background: TONE[delta.tone].bg }}
          >
            {delta.text}
          </span>
        )}
      </div>
      <div className="mt-2 truncate text-[11px] text-[#9a9da4]">{hint}</div>
    </div>
  );
}
