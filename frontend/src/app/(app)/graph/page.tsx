"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { WORKER_URL } from "@/lib/supabase";
import { PageHeader } from "@/components/ui";

// react-force-graph uses canvas/WebGL, so it must not render on the server.
const ForceGraph2D = dynamic(() => import("@/components/force-graph"), { ssr: false });

interface GNode {
  id: string;
  label: string;
  type: string;
  key?: string | null;
  props?: Record<string, string | number>;
}
interface GLink {
  source: string;
  target: string;
  type: string;
}
interface SearchHit {
  key: string;
  label: string;
  type: string;
}
interface Stats {
  nodes: number;
  edges: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
}

const TYPE_COLOR: Record<string, string> = {
  regulation: "#1d4ed8",
  regulator: "#4b40c4",
  entity_class: "#059669",
  parent_act: "#7c3aed",
  topic: "#d97706",
  deadline: "#dc2626",
};

const TYPE_LABEL: Record<string, string> = {
  regulator: "Regulator",
  entity_class: "Entity class",
  regulation: "Regulation",
  topic: "Topic",
  parent_act: "Parent act",
  deadline: "Deadline",
};

const TYPE_PLURAL: Record<string, string> = {
  regulator: "regulators",
  entity_class: "entity classes",
  regulation: "regulations",
  topic: "topics",
  parent_act: "parent acts",
  deadline: "deadlines",
};

const PRESETS = ["nbfc_mfi", "payment_aggregator", "aif", "kyc", "rbi"];

const PROP_LABEL: Record<string, string> = {
  regulator: "Regulator",
  severity: "Severity",
  document_type: "Type",
  reference_number: "Reference",
  published_date: "Published",
  requirement_count: "Requirements",
};

export default function GraphPage() {
  const [data, setData] = useState<{ nodes: GNode[]; links: GLink[] }>({ nodes: [], links: [] });
  const [center, setCenter] = useState<string | null>("nbfc_mfi");
  const [hops, setHops] = useState<1 | 2>(1);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selected, setSelected] = useState<GNode | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const [size, setSize] = useState({ w: 800, h: 520 });

  useEffect(() => {
    const url = new URL(`${WORKER_URL}/graph/subgraph`);
    if (center) url.searchParams.set("center", center);
    url.searchParams.set("hops", String(hops));
    setError(null);
    fetch(url.toString())
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setSelected(null);
      })
      .catch((e) => setError(String(e)));
  }, [center, hops]);

  useEffect(() => {
    fetch(`${WORKER_URL}/graph/stats`)
      .then((r) => r.json())
      .then(setStats)
      .catch(() => null);
  }, []);

  // Debounced center typeahead.
  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      setSearching(true);
      fetch(`${WORKER_URL}/graph/search?q=${encodeURIComponent(query.trim())}`)
        .then((r) => r.json())
        .then((h) => setHits(Array.isArray(h) ? h : []))
        .catch(() => setHits([]))
        .finally(() => setSearching(false));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    if (!wrap.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setSize({ w: entry.contentRect.width, h: Math.max(420, entry.contentRect.height) });
    });
    ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);

  const graphData = useMemo(
    () => ({ nodes: data.nodes.map((n) => ({ ...n })), links: data.links.map((l) => ({ ...l })) }),
    [data],
  );

  const pick = useCallback((key: string) => {
    setCenter(key);
    setQuery("");
    setHits([]);
  }, []);

  return (
    <div>
      <PageHeader
        title="Knowledge Graph"
        subtitle="How regulations connect to regulators, entity classes, topics, and deadlines"
      />

      {stats && (
        <div className="mb-3 flex flex-wrap gap-4 text-xs text-[var(--muted)]">
          <span>
            <b className="text-[var(--fg,#0f1b2d)]">{stats.nodes.toLocaleString()}</b> nodes
          </span>
          <span>
            <b className="text-[var(--fg,#0f1b2d)]">{stats.edges.toLocaleString()}</b> relationships
          </span>
          {Object.entries(stats.node_types)
            .sort((a, b) => b[1] - a[1])
            .map(([t, c]) => (
              <span key={t} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: TYPE_COLOR[t] ?? "#64748b" }}
                />
                {c.toLocaleString()} {TYPE_PLURAL[t] ?? t}
              </span>
            ))}
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search a regulation, topic, entity class…"
            className="w-72 rounded-lg border border-[var(--border)] bg-white px-3 py-1.5 text-xs outline-none focus:border-[#4b40c4]"
          />
          {(hits.length > 0 || searching) && query.trim().length >= 2 && (
            <div className="absolute z-50 mt-1 max-h-72 w-[26rem] overflow-auto rounded-lg border border-[var(--border)] bg-white shadow-lg">
              {searching && hits.length === 0 && (
                <div className="px-3 py-2 text-xs text-[var(--muted)]">Searching…</div>
              )}
              {hits.map((h) => (
                <button
                  key={h.key}
                  onClick={() => pick(h.key)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-slate-50"
                >
                  <span
                    className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ background: TYPE_COLOR[h.type] ?? "#64748b" }}
                  />
                  <span className="truncate">{h.label}</span>
                  <span className="ml-auto shrink-0 text-[10px] uppercase tracking-wide text-[var(--muted)]">
                    {TYPE_LABEL[h.type] ?? h.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {PRESETS.map((k) => (
          <button
            key={k}
            onClick={() => setCenter(k)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              center === k
                ? "border-[#4b40c4] bg-[#4b40c4] text-white"
                : "border-[var(--border)] bg-white text-[var(--muted)]"
            }`}
          >
            {k}
          </button>
        ))}
        <button
          onClick={() => setCenter(null)}
          className={`rounded-full border px-3 py-1 text-xs font-medium ${
            center === null
              ? "border-[#4b40c4] bg-[#4b40c4] text-white"
              : "border-[var(--border)] bg-white text-[var(--muted)]"
          }`}
        >
          overview
        </button>

        <div className="ml-auto flex items-center gap-1 text-xs text-[var(--muted)]">
          Depth
          {([1, 2] as const).map((h) => (
            <button
              key={h}
              onClick={() => setHops(h)}
              disabled={!center}
              className={`rounded-md border px-2 py-1 font-medium disabled:opacity-40 ${
                hops === h && center
                  ? "border-[#4b40c4] bg-[#4b40c4] text-white"
                  : "border-[var(--border)] bg-white text-[var(--muted)]"
              }`}
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-3">
        <div className="card min-w-0 flex-1 overflow-hidden" ref={wrap} style={{ height: 560 }}>
          {error ? (
            <div className="flex h-full items-center justify-center text-sm text-[var(--muted)]">
              Couldn&apos;t reach the worker graph endpoint ({WORKER_URL}). Start the API and seed
              the graph.
            </div>
          ) : (
            <ForceGraph2D
              graphRef={graphRef}
              graphData={graphData}
              width={size.w}
              height={size.h}
              backgroundColor="#ffffff"
              nodeRelSize={5}
              linkColor={() => "#cbd5e1"}
              linkDirectionalArrowLength={3}
              cooldownTicks={120}
              onEngineStop={() => graphRef.current?.zoomToFit(400, 40)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onNodeClick={(node: any) => setSelected(node as GNode)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, scale: number) => {
                const color = TYPE_COLOR[node.type] ?? "#64748b";
                const isSel = selected?.id === node.id;
                const isCenter = node.key && node.key === center;
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(node.x, node.y, isCenter ? 8 : 5, 0, 2 * Math.PI);
                ctx.fill();
                if (isSel || isCenter) {
                  ctx.strokeStyle = "#0f1b2d";
                  ctx.lineWidth = 1.5 / scale;
                  ctx.stroke();
                }
                if (scale > 1.2 || isSel || isCenter) {
                  ctx.fillStyle = "#0f1b2d";
                  ctx.font = `${10 / scale}px sans-serif`;
                  ctx.fillText(node.label, node.x + 7, node.y + 3);
                }
              }}
            />
          )}
        </div>

        {selected && (
          <div className="card w-80 shrink-0 overflow-auto p-4" style={{ height: 560 }}>
            <div className="mb-1 flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: TYPE_COLOR[selected.type] ?? "#64748b" }}
              />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                {TYPE_LABEL[selected.type] ?? selected.type}
              </span>
              <button
                onClick={() => setSelected(null)}
                className="ml-auto text-xs text-[var(--muted)] hover:text-black"
                aria-label="Close details"
              >
                ✕
              </button>
            </div>
            <div className="text-sm font-semibold leading-snug">{selected.label}</div>
            {selected.props?.summary && (
              <p className="mt-2 text-xs leading-relaxed text-[var(--muted)]">
                {String(selected.props.summary)}
              </p>
            )}
            <dl className="mt-3 space-y-1.5">
              {Object.entries(PROP_LABEL).map(([k, label]) =>
                selected.props?.[k] != null ? (
                  <div key={k} className="flex justify-between gap-2 text-xs">
                    <dt className="text-[var(--muted)]">{label}</dt>
                    <dd className="text-right font-medium">{String(selected.props[k])}</dd>
                  </div>
                ) : null,
              )}
            </dl>
            <div className="mt-4 flex flex-col gap-2">
              {selected.key && selected.key !== center && (
                <button
                  onClick={() => pick(selected.key!)}
                  className="rounded-lg bg-[#4b40c4] px-3 py-1.5 text-xs font-medium text-white"
                >
                  Center graph here
                </button>
              )}
              {selected.props?.source_url && (
                <a
                  href={String(selected.props.source_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-center text-xs font-medium text-[var(--muted)] hover:text-black"
                >
                  View source document ↗
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-4">
        {Object.entries(TYPE_LABEL).map(([type, label]) => (
          <div key={type} className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ background: TYPE_COLOR[type] }}
            />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
