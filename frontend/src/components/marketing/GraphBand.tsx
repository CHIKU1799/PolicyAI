"use client";

/**
 * Dark knowledge-graph band for the marketing landing page.
 * Ports the design mockup's seeded force-directed canvas field: entity-class
 * preset switcher, depth toggle, legend with per-type counts, hover isolation,
 * cursor disturbance, drag-to-pan and scroll-to-zoom. Respects
 * prefers-reduced-motion by rendering a settled, static frame instead of the
 * live simulation.
 */

import { useEffect, useMemo, useRef, useState } from "react";

const TYPE = {
  regulator: { color: "#8b7dff", label: "Regulators" },
  parent_act: { color: "#a78bfa", label: "Parent acts" },
  regulation: { color: "#4d8dff", label: "Regulations" },
  entity_class: { color: "#22c07a", label: "Entity classes" },
  topic: { color: "#f0a03c", label: "Topics" },
  deadline: { color: "#f0555c", label: "Deadlines" },
} as const;
type NodeType = keyof typeof TYPE;

type GNode = {
  id: string;
  type: NodeType;
  label: string;
  props: Record<string, string | number>;
  x: number;
  y: number;
  vx: number;
  vy: number;
  deg: number;
};
type GLink = { s: string; t: string; type: string };
type Graph = { nodes: GNode[]; links: GLink[] };

function rng(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const REGULATORS = ["RBI", "SEBI", "IRDAI", "MeitY", "PFRDA", "FIU-IND"];
const ACTS = ["RBI Act, 1934", "SEBI Act, 1992", "PMLA, 2002", "IT Act, 2000", "Insurance Act, 1938", "DPDP Act, 2023"];
const ENTITIES = [
  "NBFC-MFI", "Payment Aggregator", "AIF Cat-II", "Portfolio Manager", "Life Insurer", "Scheduled Bank",
  "Lending Service Provider", "ARC", "Housing Finance Co", "Stock Broker", "Small Finance Bank", "Payment Bank",
];
const TOPICS = [
  "KYC / CDD", "Digital Lending", "Outsourcing", "Cyber Resilience", "Grievance Redressal", "Fair Practices",
  "Data Localisation", "Capital Adequacy", "AML / CFT", "Governance", "Disclosure", "Third-party Risk",
  "Fraud Reporting", "Co-lending", "Default Loss Guarantee",
];
const DOCKINDS = ["Master Direction", "Circular", "Notification", "Guidelines", "Consultation Paper", "FAQ"];

function buildGraph(density: number): Graph {
  const r = rng(20260730);
  const nodes: GNode[] = [];
  const links: GLink[] = [];
  const add = (type: NodeType, label: string, props?: Record<string, string | number>): GNode => {
    const n: GNode = {
      id: String(nodes.length), type, label, props: props || {},
      x: (r() - 0.5) * 900, y: (r() - 0.5) * 620, vx: 0, vy: 0, deg: 0,
    };
    nodes.push(n);
    return n;
  };
  const regs = REGULATORS.map((n) => add("regulator", n, { Scope: "Statutory regulator" }));
  const acts = ACTS.map((n) => add("parent_act", n, { Kind: "Parent statute" }));
  const ents = ENTITIES.map((n) => add("entity_class", n, { Kind: "Regulated entity class" }));
  const tops = TOPICS.map((n) => add("topic", n, { Kind: "Thematic cluster" }));
  const link = (a: GNode, b: GNode, type: string) => {
    links.push({ s: a.id, t: b.id, type });
    a.deg++;
    b.deg++;
  };
  const pick = <T,>(arr: T[]): T => arr[Math.floor(r() * arr.length)];
  const regulations: GNode[] = [];
  for (let i = 0; i < density; i++) {
    const reg = pick(regs), topic = pick(tops), kind = pick(DOCKINDS);
    const yr = 2021 + Math.floor(r() * 5);
    const node = add("regulation", kind + " · " + topic.label, {
      Regulator: reg.label,
      Reference: reg.label + "/" + yr + "-" + String((yr + 1) % 100) + "/" + (10 + Math.floor(r() * 89)),
      Type: kind,
      Published: yr + "-" + String(1 + Math.floor(r() * 12)).padStart(2, "0") + "-" + String(1 + Math.floor(r() * 28)).padStart(2, "0"),
      Requirements: 3 + Math.floor(r() * 34),
      Severity: r() > 0.78 ? "High" : r() > 0.4 ? "Medium" : "Low",
    });
    node.props.summary =
      "Sets out " + (3 + Math.floor(r() * 20)) + " requirements on " + topic.label.toLowerCase() +
      " for entities supervised by " + reg.label + ".";
    regulations.push(node);
    link(node, reg, "issued_by");
    link(node, topic, "covers");
    const nEnt = 1 + Math.floor(r() * 3);
    for (let k = 0; k < nEnt; k++) link(node, pick(ents), "applies_to");
    if (r() > 0.55) link(node, pick(acts), "derives_from");
    if (r() > 0.72 && regulations.length > 4)
      link(node, regulations[Math.floor(r() * (regulations.length - 1))], r() > 0.5 ? "amends" : "supersedes");
  }
  for (let i = 0; i < Math.round(density * 0.11); i++) {
    const target = pick(regulations);
    const d = add("deadline", "Compliance due " + (2026 + Math.floor(r() * 2)) + "-" + String(1 + Math.floor(r() * 12)).padStart(2, "0"), {
      Kind: "Filing deadline",
      Regulator: target.props.Regulator,
    });
    link(d, target, "deadline_for");
  }
  for (const e of ents) for (const rg of regs) if (r() > 0.66) link(e, rg, "supervised_by");
  for (const t of tops) if (r() > 0.5) link(t, pick(acts), "grounded_in");
  return { nodes, links };
}

type Settings = {
  center: string;
  hops: number;
  off: Partial<Record<NodeType, boolean>>;
};

const PRESETS = ["NBFC-MFI", "Payment Aggregator", "AIF Cat-II", "Digital Lending", "KYC / CDD", "RBI"];

const GRAPH_STATS = [
  { value: "780+", label: "regulations tracked" },
  { value: "7,000+", label: "extracted requirements" },
  { value: "2,800+", label: "graph nodes in production" },
  { value: "< 4 hrs", label: "signal to mapped obligation" },
];

export default function GraphBand() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const graph = useMemo(() => buildGraph(160), []);
  const [center, setCenter] = useState("NBFC-MFI");
  const [hops, setHops] = useState(2);
  const [off, setOff] = useState<Partial<Record<NodeType, boolean>>>({});
  const [selected, setSelected] = useState<GNode | null>(null);
  const [disturbed, setDisturbed] = useState(false);
  const [reduced, setReduced] = useState(false);

  const settingsRef = useRef<Settings>({ center, hops, off });
  settingsRef.current = { center, hops, off };
  const simRef = useRef<{ refit: () => void; renderStatic: () => void; isReduced: boolean } | null>(null);

  const counts = useMemo(() => {
    const c: Partial<Record<NodeType, number>> = {};
    for (const n of graph.nodes) c[n.type] = (c[n.type] || 0) + 1;
    return c;
  }, [graph]);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReduced(prefersReduced);

    const byId = new Map(graph.nodes.map((n) => [n.id, n]));
    const adj = new Map<string, Set<string>>();
    for (const l of graph.links) {
      if (!adj.has(l.s)) adj.set(l.s, new Set());
      if (!adj.has(l.t)) adj.set(l.t, new Set());
      adj.get(l.s)!.add(l.t);
      adj.get(l.t)!.add(l.s);
    }
    const anchors = new Map<string, { x: number; y: number }>();
    const regs = graph.nodes.filter((n) => n.type === "regulator");
    regs.forEach((n, i) => {
      const a = (i / regs.length) * Math.PI * 2;
      anchors.set(n.id, { x: Math.cos(a) * 300, y: Math.sin(a) * 210 });
    });

    const pointer = { x: 0, y: 0, sx: 0, sy: 0, active: false };
    const cam = { x: 0, y: 0, k: 0.72, tk: 0.72 };
    const tilt = { x: 0, y: 0 };
    let hoverId: string | null = null;
    let autoFit = true;
    let dragging = false;
    let dpr = 1, w = 0, h = 0;
    let raf = 0;
    const t0 = performance.now();
    let distCache: Map<string, number> | null = null;
    let distFor = "";

    const resize = () => {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      const b = cv.getBoundingClientRect();
      cv.width = Math.max(1, b.width * dpr);
      cv.height = Math.max(1, b.height * dpr);
      w = b.width;
      h = b.height;
    };

    const focusNode = () => graph.nodes.find((n) => n.label === settingsRef.current.center) || null;

    const dist = () => {
      if (distFor === settingsRef.current.center && distCache) return distCache;
      const f = focusNode();
      const d = new Map<string, number>();
      if (f) {
        d.set(f.id, 0);
        let frontier = [f.id];
        for (let hh = 1; hh <= 3; hh++) {
          const next: string[] = [];
          for (const id of frontier)
            adj.get(id)?.forEach((nb) => {
              if (!d.has(nb)) {
                d.set(nb, hh);
                next.push(nb);
              }
            });
          frontier = next;
        }
      }
      distCache = d;
      distFor = settingsRef.current.center;
      return d;
    };

    const step = (withPointer: boolean) => {
      const N = graph.nodes, cell = 68, grid = new Map<string, GNode[]>();
      for (const n of N) {
        const k = Math.round(n.x / cell) + "," + Math.round(n.y / cell);
        if (!grid.has(k)) grid.set(k, []);
        grid.get(k)!.push(n);
      }
      for (const n of N) {
        const cx = Math.round(n.x / cell), cy = Math.round(n.y / cell);
        for (let i = -1; i <= 1; i++)
          for (let j = -1; j <= 1; j++) {
            const b = grid.get(cx + i + "," + (cy + j));
            if (!b) continue;
            for (const m of b) {
              if (m === n) continue;
              let dx = n.x - m.x, dy = n.y - m.y, d2 = dx * dx + dy * dy;
              if (d2 < 1) {
                dx = Math.random() - 0.5;
                dy = Math.random() - 0.5;
                d2 = 1;
              }
              if (d2 > 5200) continue;
              const f = 190 / d2;
              n.vx += dx * f;
              n.vy += dy * f;
            }
          }
      }
      for (const l of graph.links) {
        const a = byId.get(l.s)!, b = byId.get(l.t)!;
        const dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
        const rest = l.type === "issued_by" ? 66 : l.type === "covers" ? 82 : 118;
        const f = (d - rest) * 0.0045;
        a.vx += dx * f;
        a.vy += dy * f;
        b.vx -= dx * f;
        b.vy -= dy * f;
      }
      const focus = focusNode();
      for (const n of N) {
        const a = anchors.get(n.id);
        const gx = a ? a.x : 0, gy = a ? a.y : 0;
        const pull = a ? 0.006 : 0.0016;
        n.vx += (gx - n.x) * pull;
        n.vy += (gy - n.y) * pull;
        if (focus && n === focus) {
          n.vx += (0 - n.x) * 0.05;
          n.vy += (0 - n.y) * 0.05;
        }
        if (withPointer && pointer.active) {
          const dx = n.x - pointer.x, dy = n.y - pointer.y, d2 = dx * dx + dy * dy;
          if (d2 < 22000) {
            const f = 900 / (d2 + 220);
            n.vx += dx * f;
            n.vy += dy * f;
          }
        }
        n.vx *= 0.86;
        n.vy *= 0.86;
        n.x += Math.max(-6, Math.min(6, n.vx));
        n.y += Math.max(-6, Math.min(6, n.vy));
      }
      if (autoFit) {
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        for (const n of N) {
          if (n.x < x0) x0 = n.x;
          if (n.x > x1) x1 = n.x;
          if (n.y < y0) y0 = n.y;
          if (n.y > y1) y1 = n.y;
        }
        const pad = 56;
        const k = Math.max(0.35, Math.min(2.2, Math.min((w - pad * 2) / Math.max(1, x1 - x0), (h - pad * 2) / Math.max(1, y1 - y0))));
        cam.tk = k;
        cam.x += (-(x0 + x1) / 2 - cam.x) * 0.08;
        cam.y += (-(y0 + y1) / 2 - cam.y) * 0.08;
      }
      cam.k += (cam.tk - cam.k) * 0.12;
    };

    const radius = (n: GNode) =>
      Math.min(13, 3.4 + 1.55 * Math.sqrt(n.deg || 1)) + (n.label === settingsRef.current.center ? 2.5 : 0);

    const alphaFor = (n: GNode, d: Map<string, number>) => {
      if (settingsRef.current.off[n.type]) return 0.05;
      const dd = d.get(n.id);
      if (dd == null || dd > settingsRef.current.hops) return 0.09;
      if (hoverId) {
        if (n.id === hoverId) return 1;
        return (adj.get(hoverId) || new Set()).has(n.id) ? 0.95 : 0.1;
      }
      return dd === 0 ? 1 : 0.92 - dd * 0.12;
    };

    const draw = () => {
      const t = (performance.now() - t0) / 1000;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0d0e14";
      ctx.fillRect(0, 0, w, h);
      ctx.save();
      ctx.strokeStyle = "rgba(255,255,255,0.028)";
      ctx.lineWidth = 1;
      const gs = 44, ox = (tilt.x * 0.6) % gs, oy = (tilt.y * 0.6) % gs;
      for (let x = ox; x < w; x += gs) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = oy; y < h; y += gs) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      ctx.restore();

      ctx.save();
      ctx.translate(w / 2 + tilt.x, h / 2 + tilt.y);
      ctx.scale(cam.k, cam.k);
      ctx.translate(cam.x, cam.y);
      const d = dist();
      const hoverSet = hoverId ? adj.get(hoverId) || new Set<string>() : null;

      for (const l of graph.links) {
        const a = byId.get(l.s)!, b = byId.get(l.t)!;
        const lit = hoverId ? l.s === hoverId || l.t === hoverId : d.get(a.id) === 0 || d.get(b.id) === 0;
        const al = Math.min(alphaFor(a, d), alphaFor(b, d));
        ctx.strokeStyle = lit ? "rgba(139,125,255," + (0.75 * al + 0.2) + ")" : "rgba(150,160,190," + 0.16 * al + ")";
        ctx.lineWidth = lit ? 1.5 : 0.7;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        if (lit && !prefersReduced) {
          const p = (t * 0.45 + (a.x + b.y) * 0.004) % 1;
          ctx.fillStyle = "rgba(190,180,255,0.95)";
          ctx.beginPath();
          ctx.arc(a.x + (b.x - a.x) * p, a.y + (b.y - a.y) * p, 1.9, 0, 6.2832);
          ctx.fill();
        }
      }

      const labelled: { n: GNode; r: number; al: number }[] = [];
      for (const n of graph.nodes) {
        const al = alphaFor(n, d);
        const c = TYPE[n.type].color, r = radius(n);
        const isFocus = n.label === settingsRef.current.center, isHover = n.id === hoverId;
        ctx.globalAlpha = al;
        if (isFocus || isHover || n.deg > 14) {
          const pulse = prefersReduced ? 1 : 1 + Math.sin(t * 2 + n.x * 0.01) * 0.12;
          const gr = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, r * 3.1 * pulse);
          gr.addColorStop(0, c + "44");
          gr.addColorStop(1, c + "00");
          ctx.fillStyle = gr;
          ctx.beginPath();
          ctx.arc(n.x, n.y, r * 3.1 * pulse, 0, 6.2832);
          ctx.fill();
        }
        ctx.fillStyle = c;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, 6.2832);
        ctx.fill();
        ctx.strokeStyle = "rgba(13,14,20,0.9)";
        ctx.lineWidth = 1.4 / cam.k;
        ctx.stroke();
        if (isFocus || isHover) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1.4 / cam.k;
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 3.5 / cam.k, 0, 6.2832);
          ctx.stroke();
        }
        if (al > 0.5 && (isFocus || isHover || n.deg >= 11 || (hoverSet && hoverSet.has(n.id)) || cam.k > 1.35))
          labelled.push({ n, r, al });
        ctx.globalAlpha = 1;
      }

      const prio = (o: { n: GNode }) =>
        o.n.id === hoverId
          ? 0
          : o.n.label === settingsRef.current.center
            ? 1
            : hoverSet && hoverSet.has(o.n.id)
              ? 2
              : 3 - Math.min(0.9, o.n.deg / 60);
      labelled.sort((a, b) => prio(a) - prio(b));
      const drawn: { x0: number; y0: number; x1: number; y1: number }[] = [];
      for (const { n, r, al } of labelled) {
        const s = n.label.length > 34 ? n.label.slice(0, 32) + "…" : n.label;
        const fs = Math.max(9.5 / cam.k, 5.4);
        ctx.font = "600 " + fs + "px 'Hanken Grotesk', sans-serif";
        const tw = ctx.measureText(s).width, pad = 3.5 / cam.k, x = n.x + r + 5 / cam.k;
        const rect = { x0: x - pad, y0: n.y - fs / 2 - pad, x1: x + tw + pad, y1: n.y + fs / 2 + pad };
        let clash = false;
        for (const dr of drawn)
          if (rect.x0 < dr.x1 && rect.x1 > dr.x0 && rect.y0 < dr.y1 && rect.y1 > dr.y0) {
            clash = true;
            break;
          }
        if (clash) continue;
        drawn.push(rect);
        ctx.globalAlpha = al;
        ctx.fillStyle = "rgba(13,14,20,0.78)";
        if (typeof ctx.roundRect === "function") {
          ctx.beginPath();
          ctx.roundRect(x - pad, n.y - fs / 2 - pad, tw + pad * 2, fs + pad * 2, 3 / cam.k);
          ctx.fill();
        } else {
          ctx.fillRect(x - pad, n.y - fs / 2 - pad, tw + pad * 2, fs + pad * 2);
        }
        ctx.fillStyle = "#e7e9ee";
        ctx.textBaseline = "middle";
        ctx.fillText(s, x, n.y);
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    };

    const pickHover = () => {
      let best: GNode | null = null, bd = 16 * 16;
      for (const n of graph.nodes) {
        const dx = n.x - pointer.x, dy = n.y - pointer.y, d2 = dx * dx + dy * dy;
        if (d2 < bd) {
          bd = d2;
          best = n;
        }
      }
      const id = best ? best.id : null;
      if (id !== hoverId) {
        hoverId = id;
        cv.style.cursor = id ? "pointer" : "crosshair";
      }
    };

    const settle = (n: number) => {
      for (let i = 0; i < n; i++) step(false);
      cam.k = cam.tk;
    };

    const renderStatic = () => {
      resize();
      settle(140);
      draw();
    };

    simRef.current = {
      isReduced: prefersReduced,
      refit: () => {
        autoFit = true;
        if (prefersReduced) renderStatic();
      },
      renderStatic,
    };

    const onMove = (e: MouseEvent) => {
      if (prefersReduced) return;
      const b = cv.getBoundingClientRect();
      pointer.sx = e.clientX - b.left;
      pointer.sy = e.clientY - b.top;
      pointer.x = (pointer.sx - b.width / 2) / cam.k - cam.x;
      pointer.y = (pointer.sy - b.height / 2) / cam.k - cam.y;
      if (!pointer.active) setDisturbed(true);
      pointer.active = true;
      tilt.x = (pointer.sx / b.width - 0.5) * 26;
      tilt.y = (pointer.sy / b.height - 0.5) * 16;
      if (dragging) {
        cam.x += e.movementX / cam.k;
        cam.y += e.movementY / cam.k;
      }
      pickHover();
    };
    const onLeave = () => {
      if (pointer.active) setDisturbed(false);
      pointer.active = false;
      hoverId = null;
      tilt.x = 0;
      tilt.y = 0;
    };
    const onDown = () => {
      dragging = true;
      autoFit = false;
    };
    const onUp = () => {
      dragging = false;
      if (hoverId) {
        const n = byId.get(hoverId);
        if (n) setSelected(n);
      }
    };
    const onWheel = (e: WheelEvent) => {
      if (prefersReduced) return;
      e.preventDefault();
      autoFit = false;
      cam.tk = Math.max(0.3, Math.min(2.4, cam.tk * (e.deltaY > 0 ? 0.9 : 1.11)));
    };

    cv.addEventListener("mousemove", onMove);
    cv.addEventListener("mouseleave", onLeave);
    cv.addEventListener("mousedown", onDown);
    cv.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("mouseup", onUp);
    const ro = new ResizeObserver(() => {
      resize();
      if (prefersReduced) draw();
    });
    ro.observe(cv);
    resize();

    if (prefersReduced) {
      renderStatic();
    } else {
      const loop = () => {
        step(true);
        draw();
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      cv.removeEventListener("mousemove", onMove);
      cv.removeEventListener("mouseleave", onLeave);
      cv.removeEventListener("mousedown", onDown);
      cv.removeEventListener("wheel", onWheel);
      window.removeEventListener("mouseup", onUp);
      simRef.current = null;
    };
  }, [graph]);

  // Re-fit the camera (and re-render the static frame under reduced motion)
  // whenever the framing settings change.
  useEffect(() => {
    simRef.current?.refit();
  }, [center, hops]);
  useEffect(() => {
    if (simRef.current?.isReduced) simRef.current.renderStatic();
  }, [off]);

  const monoChip = (on: boolean) =>
    on
      ? { background: "#4B40C4", color: "#fff", borderColor: "#5B4FD6" }
      : { background: "transparent", color: "#9AA0AB", borderColor: "#282A35" };

  return (
    <div
      className="overflow-hidden rounded-3xl border"
      style={{ background: "#0D0E14", borderColor: "#1C1D27", boxShadow: "0 40px 90px -40px rgba(13,14,20,.8)" }}
    >
      {/* control bar */}
      <div className="flex flex-wrap items-center gap-2.5 border-b px-4 py-4 sm:px-5" style={{ borderColor: "#1C1D27" }}>
        <span className="mono text-[10.5px] font-medium tracking-[.14em]" style={{ color: "#8B8F99" }}>
          CENTER
        </span>
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => {
              setCenter(p);
              setSelected(null);
            }}
            className="mono rounded-full border px-[11px] py-[5px] text-[11px] font-semibold"
            style={monoChip(center === p)}
          >
            {p}
          </button>
        ))}
        <span
          className="mono ml-auto flex items-center gap-[7px] text-[10.5px] tracking-[.14em]"
          style={{ color: "#8B8F99" }}
        >
          DEPTH
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setHops(d)}
              className="mono rounded-lg border px-2.5 py-1 text-[11px] font-semibold"
              style={monoChip(hops === d)}
            >
              {d}
            </button>
          ))}
        </span>
      </div>
      {/* field */}
      <div className="relative">
        <canvas ref={canvasRef} className="block h-[440px] w-full cursor-crosshair md:h-[620px]" />
        <div className="pointer-events-none absolute left-4 top-[18px] flex flex-col gap-[18px] sm:left-5">
          <div className="mono flex gap-3.5 whitespace-nowrap text-[11px]" style={{ color: "#C9CCD4" }}>
            <span>
              <b style={{ color: "#fff" }}>{graph.nodes.length.toLocaleString("en-IN")}</b> nodes
            </span>
            <span>
              <b style={{ color: "#fff" }}>{graph.links.length.toLocaleString("en-IN")}</b> edges
            </span>
            <span style={{ color: "#6EE7A8" }}>
              {reduced ? "static field" : disturbed ? "field disturbed" : "● simulating"}
            </span>
          </div>
          <div className="pointer-events-auto hidden flex-col gap-[5px] sm:flex">
            {(Object.entries(TYPE) as [NodeType, (typeof TYPE)[NodeType]][]).map(([k, v]) => (
              <button
                key={k}
                type="button"
                onClick={() => setOff((s) => ({ ...s, [k]: !s[k] }))}
                className="flex items-center gap-2 text-left text-[11.5px] font-semibold"
                style={{ color: off[k] ? "#5F636E" : "#C9CCD4" }}
              >
                <span
                  className="h-[9px] w-[9px] rounded-full"
                  style={{ background: off[k] ? "#3A3D48" : v.color }}
                  aria-hidden
                />
                {v.label}
                <span className="mono text-[10px]" style={{ color: "#6D717C" }}>
                  {counts[k] || 0}
                </span>
              </button>
            ))}
          </div>
        </div>
        <div
          className="mono pointer-events-none absolute bottom-[18px] right-5 hidden text-[10.5px] tracking-[.06em] md:block"
          style={{ color: "#5F636E" }}
        >
          {reduced ? "STATIC FIELD · MOTION REDUCED" : "CURSOR FIELD ACTIVE · DRAG TO PAN · SCROLL TO ZOOM"}
        </div>
        {selected && (
          <div
            className="anim-rise absolute right-4 top-[18px] w-[272px] max-w-[calc(100%-32px)] rounded-2xl border p-4 sm:right-5 sm:w-[288px]"
            style={{
              background: "rgba(18,19,26,.92)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
              borderColor: "#262833",
            }}
          >
            <div className="mb-[9px] flex items-center gap-2">
              <span className="h-[9px] w-[9px] rounded-full" style={{ background: TYPE[selected.type].color }} aria-hidden />
              <span className="mono text-[10px] tracking-[.14em]" style={{ color: "#8B8F99" }}>
                {TYPE[selected.type].label.replace(/s$/, "").toUpperCase()}
              </span>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setSelected(null)}
                className="ml-auto text-[13px]"
                style={{ color: "#8B8F99" }}
              >
                ✕
              </button>
            </div>
            <div className="text-[14px] font-semibold leading-snug" style={{ color: "#F2F3F5" }}>
              {selected.label}
            </div>
            <div className="mt-2 text-[12px] leading-relaxed" style={{ color: "#9AA0AB" }}>
              {String(selected.props.summary || `Connected to ${selected.deg} other nodes in the corpus.`)}
            </div>
            <div className="mt-3 flex flex-col gap-1.5">
              {Object.entries(selected.props)
                .filter(([k]) => k !== "summary")
                .slice(0, 6)
                .map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2.5 text-[11.5px]">
                    <span style={{ color: "#7C818C" }}>{k}</span>
                    <span className="text-right font-semibold" style={{ color: "#DFE2E7" }}>
                      {String(v)}
                    </span>
                  </div>
                ))}
            </div>
            <button
              type="button"
              onClick={() => {
                setCenter(selected.label);
                setSelected(null);
              }}
              className="mt-[13px] w-full rounded-[10px] py-[9px] text-[12px] font-semibold text-white"
              style={{ background: "#4B40C4" }}
            >
              Center graph here
            </button>
          </div>
        )}
      </div>
      {/* stats row */}
      <div className="grid grid-cols-2 border-t md:grid-cols-4" style={{ borderColor: "#1C1D27" }}>
        {GRAPH_STATS.map((s) => (
          <div key={s.label} className="border-r px-4 py-4 last:border-r-0 sm:px-5" style={{ borderColor: "#1C1D27" }}>
            <div className="text-[20px] font-bold tracking-tight text-white sm:text-[23px]">{s.value}</div>
            <div className="mt-[3px] text-[11.5px]" style={{ color: "#8B8F99" }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
