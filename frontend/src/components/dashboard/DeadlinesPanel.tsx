"use client";

/** "Upcoming deadlines" side panel: real tasks.due_date within the next 30
 *  days, soonest first. Date chip is tinted by proximity (this week red,
 *  next two weeks amber, later slate), like the mock. */

import type { Task } from "@/lib/types";
import { Shimmer } from "@/components/Loading";

function chipColor(daysLeft: number): string {
  if (daysLeft <= 7) return "#C0392B";
  if (daysLeft <= 14) return "#B4661F";
  return "#54565E";
}

function chipDate(iso: string): string {
  return new Date(`${iso}T00:00:00`)
    .toLocaleDateString("en-GB", { day: "2-digit", month: "short" })
    .toUpperCase();
}

export default function DeadlinesPanel({ tasks, loading }: { tasks: Task[]; loading: boolean }) {
  const today = new Date().toISOString().slice(0, 10);
  const horizon = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
  const upcoming = tasks
    .filter((t) => t.status !== "done" && t.due_date && t.due_date >= today && t.due_date <= horizon)
    .sort((a, b) => a.due_date!.localeCompare(b.due_date!))
    .slice(0, 5);

  return (
    <div className="card p-5 shadow-[0_1px_2px_rgba(17,18,27,.04)]">
      <div className="text-[10px] font-bold uppercase tracking-[.09em] text-[#aeaeb4]">Next 30 days</div>
      <div className="mb-2 mt-0.5 text-[13.5px] font-bold">Upcoming deadlines</div>
      {loading &&
        Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 border-t border-[var(--hairline)] py-[9px]">
            <Shimmer className="h-6 w-14 flex-none" />
            <Shimmer className="h-3.5 flex-1" />
          </div>
        ))}
      {!loading && upcoming.length === 0 && (
        <div className="border-t border-[var(--hairline)] pt-3 text-[13px] text-[var(--muted)]">
          No task deadlines in the next 30 days.
        </div>
      )}
      {!loading &&
        upcoming.map((t) => {
          const daysLeft = Math.ceil(
            (new Date(`${t.due_date}T00:00:00`).getTime() - Date.now()) / 864e5,
          );
          const color = chipColor(daysLeft);
          return (
            <div key={t.id} className="flex items-center gap-3 border-t border-[var(--hairline)] py-[9px]">
              <span
                className="mono w-[54px] flex-none rounded-lg border border-[#eae9e5] py-1 text-center text-[10px] font-semibold leading-none"
                style={{ color }}
              >
                {chipDate(t.due_date!)}
              </span>
              <span className="min-w-0 flex-1 truncate text-[12.5px] leading-snug text-[#3a3d44]" title={t.title}>
                {t.title}
              </span>
            </div>
          );
        })}
    </div>
  );
}
