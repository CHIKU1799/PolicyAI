"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { getSupabase } from "@/lib/supabase";
import type { Alert } from "@/lib/types";

export default function AlertFeed() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;

    supabase
      .from("alerts")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(20)
      .then(({ data }) => setAlerts((data as Alert[]) ?? []));

    const channel = supabase
      .channel("alerts-feed")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "alerts" },
        (payload) => setAlerts((prev) => [payload.new as Alert, ...prev].slice(0, 20)),
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const unread = alerts.filter((a) => !a.read_at).length;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-lg border border-[var(--border)] bg-white p-2 text-slate-600 hover:text-slate-900"
        aria-label="Alerts"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 card max-h-96 overflow-y-auto shadow-xl">
          <div className="border-b border-[var(--border)] px-4 py-2 text-sm font-semibold">
            Live alerts
          </div>
          {alerts.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-[var(--muted)]">
              No alerts yet. New regulations and obligations appear here in real time.
            </div>
          )}
          {alerts.map((a) => (
            <div key={a.id} className="border-b border-[var(--border)] px-4 py-2.5 text-sm last:border-0">
              <div className="text-slate-800">{a.message}</div>
              <div className="mt-0.5 text-[11px] text-[var(--muted)]">
                {a.kind.replace(/_/g, " ")} · {new Date(a.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
