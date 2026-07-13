"use client";

import { useEffect, useState } from "react";
import { ExternalLink, FileSearch, X } from "lucide-react";
import { WORKER_URL, workerFetch } from "@/lib/supabase";
import { Badge } from "@/components/ui";

interface Hit {
  key: string;
  label: string;
  type: string;
}

interface Assessment {
  regulation_key: string;
  regulation_title: string;
  source_url: string | null;
  applicability: string;
  overall_severity: string;
  summary: string;
  affected_areas: string[];
  key_requirements: string[];
  suggested_actions: { action: string; priority: string }[];
}

const SEV_STYLE: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-emerald-100 text-emerald-700",
};

const PRIORITY_STYLE: Record<string, string> = {
  immediate: "bg-red-100 text-red-700",
  short_term: "bg-amber-100 text-amber-700",
  monitor: "bg-slate-100 text-slate-600",
};

export default function ImpactAssessment() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [picked, setPicked] = useState<Hit | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Assessment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      fetch(`${WORKER_URL}/graph/search?q=${encodeURIComponent(query.trim())}`)
        .then((r) => r.json())
        .then((h: Hit[]) => setHits((Array.isArray(h) ? h : []).filter((x) => x.type === "regulation")))
        .catch(() => setHits([]));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  async function draft() {
    if (!picked || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const resp = await workerFetch("/ask/impact-assessment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ regulation_key: picked.key }),
      });
      if (!resp.ok) throw new Error(`worker responded ${resp.status}`);
      setResult(await resp.json());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
        <FileSearch size={16} className="text-[var(--brand)]" />
        Draft an impact assessment
        <span className="text-xs font-normal text-[var(--muted)]">
          pick a regulation, get an analyst first pass to review
        </span>
      </div>

      <div className="flex items-center gap-2">
        {picked ? (
          <span className="inline-flex max-w-[70%] items-center gap-2 rounded-lg border border-[var(--brand)] bg-indigo-50 px-3 py-1.5 text-xs text-slate-800">
            <span className="truncate">{picked.label}</span>
            <button onClick={() => setPicked(null)} aria-label="Clear regulation">
              <X size={13} className="text-[var(--muted)]" />
            </button>
          </span>
        ) : (
          <div className="relative flex-1">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search a regulation, e.g. digital lending…"
              className="w-full rounded-lg border border-[var(--border)] bg-white px-3 py-1.5 text-xs outline-none focus:border-[var(--brand)]"
            />
            {hits.length > 0 && (
              <div className="absolute z-50 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-[var(--border)] bg-white shadow-lg">
                {hits.map((h) => (
                  <button
                    key={h.key}
                    onClick={() => {
                      setPicked(h);
                      setQuery("");
                      setHits([]);
                    }}
                    className="block w-full truncate px-3 py-2 text-left text-xs hover:bg-slate-50"
                  >
                    {h.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <button
          onClick={draft}
          disabled={!picked || busy}
          className="rounded-lg bg-[#4b40c4] px-4 py-1.5 text-xs font-medium text-white hover:bg-[#3a2fb0] disabled:opacity-60"
        >
          {busy ? "Drafting…" : "Draft"}
        </button>
      </div>

      {busy && (
        <div className="mt-3 text-xs text-[var(--muted)]">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--brand)]" />
            Reading the regulation&apos;s requirements against your profile…
          </span>
        </div>
      )}
      {error && <div className="mt-3 text-xs text-red-600">Couldn&apos;t draft: {error}</div>}

      {result && (
        <div className="mt-4 space-y-3 border-t border-[var(--border)] pt-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="font-semibold leading-snug text-slate-800">
              {result.regulation_title}
            </div>
            <Badge className={SEV_STYLE[result.overall_severity] ?? "bg-slate-100"}>
              {result.overall_severity} impact
            </Badge>
          </div>
          <p className="text-xs leading-relaxed text-slate-700">{result.summary}</p>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Applicability
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-700">{result.applicability}</p>
          </div>
          {result.affected_areas.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.affected_areas.map((a) => (
                <span
                  key={a}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600"
                >
                  {a}
                </span>
              ))}
            </div>
          )}
          {result.key_requirements.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                Requirements that bite hardest
              </div>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-700">
                {result.key_requirements.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          {result.suggested_actions.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                Suggested actions
              </div>
              <ul className="mt-1.5 space-y-1.5">
                {result.suggested_actions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
                    <Badge className={PRIORITY_STYLE[a.priority] ?? "bg-slate-100"}>
                      {a.priority.replace("_", " ")}
                    </Badge>
                    <span className="leading-relaxed">{a.action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.source_url && (
            <a
              href={result.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              Source document <ExternalLink size={11} />
            </a>
          )}
        </div>
      )}
    </div>
  );
}
