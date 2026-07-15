"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { WORKER_URL } from "@/lib/supabase";
import { sbSearch, sbStats, sbSubgraph } from "@/lib/graphFallback";
import { PageHeader } from "@/components/ui";
import { ProcessOverlay } from "@/components/Loading";

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
  const [loading, setLoading] = useState(true);
  const wrap = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const [size, setSize] = useState({ w: 800, h: 520 });

  useEffect(() => {
    const url = new URL(`${WORKER_URL}/graph/subgraph`);
    if (center) url.searchParams.set("center", center);
    url.searchParams.set("hops", String(hops));
    setError(null);
    setLoading(true);
    fetch(url.toString())
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setSelected(null);
      })
      // Worker unreachable (e.g. deployed frontend without the worker tier):
      // read the shared corpus straight from Supabase instead.
      .catch(() =>
        sbSubgraph(center, hops)
          .then((d) => {
            if (d) {
              setData(d);
              setSelected(null);
            } else setError("no data source reachable");
          })
          .catch((e) => setError(String(e))),
      )
      .finally(() => setLoading(false));
  }, [center, hops]);

  useEffect(() => {
    fetch(`${WORKER_URL}/graph/stats`)
      .then((r) => r.json())
      .then(setStats)
      .catch(() => sbStats().then((st) => st && setStats(st)).catch(() => null));
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
        .catch(() => sbSearch(query.trim()).then(setHits).catch(() => setHits([])))
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

  // Degree map + adjacency, for hub-sized nodes and hover highlighting.
  const { degree, neighbors } = useMemo(() => {
    const deg = new Map<string, number>();
    const adj = new Map<string, Set<string>>();
    for (const l of data.links) {
      deg.set(l.source, (deg.get(l.source) ?? 0) + 1);
      deg.set(l.target, (deg.get(l.target) ?? 0) + 1);
      if (!adj.has(l.source)) adj.set(l.source, new Set());
      if (!adj.has(l.target)) adj.set(l.target, new Set());
      adj.get(l.source)!.add(l.target);
      adj.get(l.target)!.add(l.source);
    }
    return { degree: deg, neighbors: adj };
  }, [data]);

  const [hover, setHover] = useState<GNode | null>(null);
  // force-graph rewrites link endpoints from ids to node objects once mounted
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const endId = (e: any): string => (typeof e === "object" && e ? e.id : e);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const touchesFocus = (l: any) => {
    const focus = hover?.id ?? (center ? data.nodes.find((n) => n.key === center)?.id : undefined);
    if (!focus) return false;
    return endId(l.source) === focus || endId(l.target) === focus;
  };
  const nodeRadius = (id: string, isCenter: boolean) =>
    Math.min(13, 3.5 + 1.7 * Math.sqrt(degree.get(id) ?? 1)) + (isCenter ? 2 : 0);

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
        <div className="card relative min-w-0 flex-1 overflow-hidden" ref={wrap} style={{ height: 560 }}>
          {loading && <ProcessOverlay label="Building the knowledge graph…" />}
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
              autoPauseRedraw={false}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              linkColor={(l: any) => {
                if (touchesFocus(l)) return "rgba(75,64,196,0.55)";
                return hover ? "rgba(203,213,225,0.25)" : "#d7dde7";
              }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              linkWidth={(l: any) => (touchesFocus(l) ? 1.8 : 1)}
              linkDirectionalArrowLength={3}
              // a slow pulse of particles along the focused node's relationships
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              linkDirectionalParticles={(l: any) => (touchesFocus(l) ? 2 : 0)}
              linkDirectionalParticleSpeed={0.004}
              linkDirectionalParticleWidth={2.2}
              linkDirectionalParticleColor={() => "#4b40c4"}
              cooldownTicks={120}
              onEngineStop={() => graphRef.current?.zoomToFit(400, 40)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onNodeClick={(node: any) => setSelected(node as GNode)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onNodeHover={(node: any) => setHover((node as GNode) ?? null)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, scale: number) => {
                if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) return;
                const color = TYPE_COLOR[node.type] ?? "#64748b";
                const isSel = selected?.id === node.id;
                const isCenter = node.key && node.key === center;
                const isHover = hover?.id === node.id;
                const dimmed =
                  hover !== null && !isHover && !(neighbors.get(hover.id)?.has(node.id) ?? false);
                const r = nodeRadius(node.id, Boolean(isCenter));

                ctx.globalAlpha = dimmed ? 0.16 : 1;
                // soft halo behind hubs and the focus node
                if ((isCenter || isHover || isSel) && !dimmed) {
                  const halo = ctx.createRadialGradient(node.x, node.y, r, node.x, node.y, r * 2.4);
                  halo.addColorStop(0, `${color}33`);
                  halo.addColorStop(1, `${color}00`);
                  ctx.fillStyle = halo;
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, r * 2.4, 0, 2 * Math.PI);
                  ctx.fill();
                }
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
                ctx.fill();
                // 2px surface ring separates overlapping marks
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 1.6 / scale;
                ctx.stroke();
                if (isSel || isCenter) {
                  ctx.strokeStyle = "#0f1b2d";
                  ctx.lineWidth = 1.6 / scale;
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, r + 2.4 / scale, 0, 2 * Math.PI);
                  ctx.stroke();
                }

                const isHub = (degree.get(node.id) ?? 0) >= 12;
                if ((scale > 1.3 || isSel || isCenter || isHover || isHub) && !dimmed) {
                  const label: string =
                    node.label.length > 44 ? `${node.label.slice(0, 42)}…` : node.label;
                  const fontSize = Math.max(10 / scale, 3.2);
                  ctx.font = `${isCenter || isHover ? 600 : 400} ${fontSize}px 'Hanken Grotesk', sans-serif`;
                  const w = ctx.measureText(label).width;
                  const px = 4 / scale;
                  const x = node.x + r + 4 / scale;
                  const y = node.y;
                  ctx.fillStyle = "rgba(255,255,255,0.88)";
                  ctx.beginPath();
                  ctx.roundRect(x - px, y - fontSize / 2 - px, w + px * 2, fontSize + px * 2, 3 / scale);
                  ctx.fill();
                  ctx.fillStyle = "#1e293b";
                  ctx.textBaseline = "middle";
                  ctx.fillText(label, x, y);
                }
                ctx.globalAlpha = 1;
              }}
              // keep the click/hover target as big as the drawn mark
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              nodePointerAreaPaint={(node: any, paintColor: string, ctx: CanvasRenderingContext2D) => {
                ctx.fillStyle = paintColor;
                ctx.beginPath();
                ctx.arc(node.x, node.y, nodeRadius(node.id, node.key === center) + 2, 0, 2 * Math.PI);
                ctx.fill();
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
