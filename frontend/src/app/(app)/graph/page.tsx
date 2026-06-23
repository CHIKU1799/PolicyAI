"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { WORKER_URL } from "@/lib/supabase";
import { PageHeader } from "@/components/ui";

// react-force-graph uses canvas/WebGL — must not render on the server.
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface GNode {
  id: string;
  label: string;
  type: string;
}
interface GLink {
  source: string;
  target: string;
  type: string;
}

const TYPE_COLOR: Record<string, string> = {
  regulation: "#1d4ed8",
  regulator: "#0b1f4d",
  entity_class: "#059669",
  parent_act: "#7c3aed",
  topic: "#d97706",
  deadline: "#dc2626",
};

const LEGEND = [
  { type: "regulator", label: "Regulator" },
  { type: "entity_class", label: "Entity class" },
  { type: "regulation", label: "Regulation" },
  { type: "topic", label: "Topic" },
  { type: "parent_act", label: "Parent act" },
  { type: "deadline", label: "Deadline" },
];

export default function GraphPage() {
  const [data, setData] = useState<{ nodes: GNode[]; links: GLink[] }>({ nodes: [], links: [] });
  const [center, setCenter] = useState("nbfc_mfi");
  const [error, setError] = useState<string | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 520 });

  useEffect(() => {
    const url = new URL(`${WORKER_URL}/graph/subgraph`);
    if (center) url.searchParams.set("center", center);
    fetch(url.toString())
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [center]);

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

  return (
    <div>
      <PageHeader
        title="Knowledge Graph"
        subtitle="How regulations connect to regulators, entity classes, topics, and deadlines"
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-[var(--muted)]">Center on:</span>
        {["nbfc_mfi", "payment_aggregator", "aif", "life_insurer", "rbi"].map((k) => (
          <button
            key={k}
            onClick={() => setCenter(k)}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              center === k
                ? "border-[#0b1f4d] bg-[#0b1f4d] text-white"
                : "border-[var(--border)] bg-white text-[var(--muted)]"
            }`}
          >
            {k}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden" ref={wrap} style={{ height: 540 }}>
        {error ? (
          <div className="flex h-full items-center justify-center text-sm text-[var(--muted)]">
            Couldn&apos;t reach the worker graph endpoint ({WORKER_URL}). Start the API and seed the graph.
          </div>
        ) : (
          <ForceGraph2D
            graphData={graphData}
            width={size.w}
            height={size.h}
            backgroundColor="#ffffff"
            nodeRelSize={5}
            linkColor={() => "#cbd5e1"}
            linkDirectionalArrowLength={3}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, scale: number) => {
              const color = TYPE_COLOR[node.type] ?? "#64748b";
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI);
              ctx.fill();
              if (scale > 1.2) {
                ctx.fillStyle = "#0f1b2d";
                ctx.font = `${10 / scale}px sans-serif`;
                ctx.fillText(node.label, node.x + 7, node.y + 3);
              }
            }}
          />
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-4">
        {LEGEND.map((l) => (
          <div key={l.type} className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ background: TYPE_COLOR[l.type] }}
            />
            {l.label}
          </div>
        ))}
      </div>
    </div>
  );
}
