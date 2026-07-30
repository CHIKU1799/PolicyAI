"use client";

/** Mock-styled horizontal severity bars: label left, count right, thin
 *  rounded bar underneath sized by share of the total. */

import { Shimmer } from "@/components/Loading";

export interface SeverityBarItem {
  label: string;
  count: number;
  color: string;
}

export default function SeverityBars({
  kicker,
  title,
  items,
  emptyText,
  loading,
}: {
  kicker: string;
  title: string;
  items: SeverityBarItem[];
  emptyText: string;
  loading: boolean;
}) {
  const total = items.reduce((sum, i) => sum + i.count, 0);
  return (
    <div className="card p-5 shadow-[0_1px_2px_rgba(17,18,27,.04)]">
      <div className="text-[10px] font-bold uppercase tracking-[.09em] text-[#aeaeb4]">{kicker}</div>
      <div className="mb-3 mt-0.5 text-[13.5px] font-bold">{title}</div>
      {loading &&
        Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="mb-3 last:mb-0">
            <Shimmer className="mb-1.5 h-3 w-24" />
            <Shimmer className="h-1.5 w-full" />
          </div>
        ))}
      {!loading && total === 0 && <div className="text-[13px] text-[var(--muted)]">{emptyText}</div>}
      {!loading &&
        total > 0 &&
        items
          .filter((i) => i.count > 0)
          .map((i) => (
            <div key={i.label} className="mb-3 last:mb-0">
              <div className="mb-1 flex justify-between text-[11px] text-[#54565e]">
                <span className="capitalize">{i.label}</span>
                <span className="font-bold tabular-nums" style={{ color: i.color }}>
                  {i.count}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-[#f0f0ec]">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(i.count / total) * 100}%`, background: i.color }}
                />
              </div>
            </div>
          ))}
    </div>
  );
}
