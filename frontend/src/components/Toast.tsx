"use client";

import { useEffect, useState } from "react";
import { Check, AlertCircle } from "lucide-react";

type Toast = { id: number; msg: string; type: "ok" | "error" };

let _id = 0;
const listeners = new Set<(t: Toast) => void>();

/** Fire a toast from anywhere (client components only). */
export function toast(msg: string, type: "ok" | "error" = "ok") {
  const t = { id: ++_id, msg, type };
  listeners.forEach((l) => l(t));
}

export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);

  useEffect(() => {
    const on = (t: Toast) => {
      setItems((x) => [...x, t]);
      setTimeout(() => setItems((x) => x.filter((i) => i.id !== t.id)), 3200);
    };
    listeners.add(on);
    return () => {
      listeners.delete(on);
    };
  }, []);

  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className="anim-in pointer-events-auto flex items-center gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2.5 text-[13px] shadow-lg"
        >
          <span
            className={`flex h-5 w-5 flex-none items-center justify-center rounded-full ${
              t.type === "ok" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
            }`}
          >
            {t.type === "ok" ? <Check size={12} /> : <AlertCircle size={12} />}
          </span>
          <span className="text-[var(--text-2)]">{t.msg}</span>
        </div>
      ))}
    </div>
  );
}
