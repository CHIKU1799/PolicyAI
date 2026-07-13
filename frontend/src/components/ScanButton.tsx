"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import clsx from "clsx";
import { workerFetch } from "@/lib/supabase";

export default function ScanButton() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function scan() {
    setBusy(true);
    setMsg(null);
    try {
      const resp = await workerFetch("/scan", { method: "POST" });
      if (!resp.ok) throw new Error(`worker responded ${resp.status}`);
      setMsg("Scan started — new items will appear as they're processed.");
    } catch (err) {
      setMsg(`Couldn't reach the worker (${(err as Error).message}).`);
    } finally {
      setBusy(false);
      setTimeout(() => setMsg(null), 6000);
    }
  }

  return (
    <div className="flex items-center gap-3">
      {msg && <span className="text-xs text-[var(--muted)]">{msg}</span>}
      <button
        onClick={scan}
        disabled={busy}
        className="inline-flex items-center gap-2 rounded-lg bg-[#4b40c4] px-3 py-2 text-sm font-medium text-white hover:bg-[#3a2fb0] disabled:opacity-60"
      >
        <RefreshCw size={16} className={clsx(busy && "animate-spin")} />
        {busy ? "Scanning…" : "Scan now"}
      </button>
    </div>
  );
}
