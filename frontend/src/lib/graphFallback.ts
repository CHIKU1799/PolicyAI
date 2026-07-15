"use client";

/**
 * Supabase-direct fallback for the knowledge-graph explorer, used when the
 * worker API is unreachable (e.g. the deployed frontend before the worker
 * tier exists). Nodes/edges are the shared regulatory corpus, so reading them
 * with the public client is safe and RLS-compatible.
 */

import { getSupabase } from "@/lib/supabase";

export interface FNode {
  id: string;
  label: string;
  type: string;
  key: string | null;
  props: Record<string, string | number>;
}
export interface FLink {
  source: string;
  target: string;
  type: string;
}

const NODE_TYPES = ["regulation", "regulator", "entity_class", "parent_act", "topic", "deadline"];
const EDGE_TYPES = [
  "amends",
  "supersedes",
  "issued_by",
  "applies_to",
  "derived_from",
  "covers_topic",
  "has_deadline",
  "references",
];
const DETAIL_KEYS = [
  "summary",
  "regulator",
  "severity",
  "document_type",
  "reference_number",
  "published_date",
  "source_url",
  "requirement_count",
  "name",
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toNode(row: any): FNode {
  const p = row.properties ?? {};
  return {
    id: row.id,
    label: p.short_name || p.name || p.title || p.canonical_key || "?",
    type: row.node_type,
    key: p.canonical_key ?? null,
    props: Object.fromEntries(DETAIL_KEYS.filter((k) => p[k] != null).map((k) => [k, p[k]])),
  };
}

export async function sbStats() {
  const supabase = getSupabase();
  if (!supabase) return null;
  const nodeCounts = await Promise.all(
    NODE_TYPES.map(async (t) => {
      const { count } = await supabase
        .from("nodes")
        .select("id", { count: "exact", head: true })
        .eq("node_type", t);
      return [t, count ?? 0] as const;
    }),
  );
  const edgeCounts = await Promise.all(
    EDGE_TYPES.map(async (t) => {
      const { count } = await supabase
        .from("edges")
        .select("id", { count: "exact", head: true })
        .eq("edge_type", t);
      return [t, count ?? 0] as const;
    }),
  );
  const node_types = Object.fromEntries(nodeCounts.filter(([, c]) => c > 0));
  const edge_types = Object.fromEntries(edgeCounts.filter(([, c]) => c > 0));
  return {
    nodes: Object.values(node_types).reduce((a, b) => a + b, 0),
    edges: Object.values(edge_types).reduce((a, b) => a + b, 0),
    node_types,
    edge_types,
  };
}

export async function sbSearch(q: string) {
  const supabase = getSupabase();
  if (!supabase) return [];
  const like = `%${q.replace(/[%_]/g, "")}%`;
  const { data } = await supabase
    .from("nodes")
    .select("id, node_type, properties")
    .or(
      `properties->>title.ilike.${like},properties->>name.ilike.${like},properties->>canonical_key.ilike.${like}`,
    )
    .limit(12);
  return (data ?? [])
    .map(toNode)
    .filter((n) => n.key)
    .map((n) => ({ key: n.key!, label: n.label, type: n.type }));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function edgesTouching(supabase: any, ids: string[]): Promise<any[]> {
  const chunks: string[][] = [];
  for (let i = 0; i < ids.length; i += 80) chunks.push(ids.slice(i, i + 80));
  const out: FLink[] = [];
  for (const chunk of chunks) {
    const list = chunk.join(",");
    const { data } = await supabase
      .from("edges")
      .select("source_id, target_id, edge_type")
      .or(`source_id.in.(${list}),target_id.in.(${list})`)
      .limit(400);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (data ?? []).forEach((e: any) => out.push(e));
  }
  return out;
}

export async function sbSubgraph(
  center: string | null,
  hops: number,
): Promise<{ nodes: FNode[]; links: FLink[] } | null> {
  const supabase = getSupabase();
  if (!supabase) return null;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let rawEdges: any[] = [];
  let rootId: string | null = null;
  if (center) {
    const { data: roots } = await supabase
      .from("nodes")
      .select("id")
      .eq("properties->>canonical_key", center)
      .limit(1);
    if (!roots?.length) return { nodes: [], links: [] };
    rootId = roots[0].id as string;
    rawEdges = await edgesTouching(supabase, [rootId]);
    if (hops === 2) {
      const frontier = new Set<string>();
      rawEdges.forEach((e) => {
        frontier.add(e.source_id);
        frontier.add(e.target_id);
      });
      frontier.delete(rootId);
      const second = await edgesTouching(supabase, Array.from(frontier).slice(0, 160));
      const seen = new Set(rawEdges.map((e) => `${e.source_id}|${e.target_id}|${e.edge_type}`));
      for (const e of second) {
        const k = `${e.source_id}|${e.target_id}|${e.edge_type}`;
        if (!seen.has(k) && rawEdges.length < 260) {
          seen.add(k);
          rawEdges.push(e);
        }
      }
    }
  } else {
    const { data } = await supabase
      .from("edges")
      .select("source_id, target_id, edge_type")
      .limit(200);
    rawEdges = data ?? [];
  }

  const ids = new Set<string>();
  rawEdges.forEach((e) => {
    ids.add(e.source_id);
    ids.add(e.target_id);
  });
  if (rootId) ids.add(rootId);

  const nodeRows: FNode[] = [];
  const idList = Array.from(ids);
  for (let i = 0; i < idList.length; i += 100) {
    const { data } = await supabase
      .from("nodes")
      .select("id, node_type, properties")
      .in("id", idList.slice(i, i + 100));
    (data ?? []).forEach((r) => nodeRows.push(toNode(r)));
  }

  return {
    nodes: nodeRows,
    links: rawEdges.map((e) => ({ source: e.source_id, target: e.target_id, type: e.edge_type })),
  };
}
