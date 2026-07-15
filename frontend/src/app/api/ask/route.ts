import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

/**
 * Serverless backup for "Ask PolicyAI", used when the Python worker tier is
 * not deployed (e.g. the Vercel-only setup). Grounds the answer in the
 * caller's own Supabase data (their RLS applies: we query with their token)
 * plus a keyword search over the shared regulation graph, then answers via a
 * provider chain that prefers free tiers and ends at a cheap paid fallback:
 * Groq -> Cerebras -> Gemini -> Mistral -> OpenRouter -> Anthropic (Haiku).
 * Each slot activates only when its key is configured; auth is required so
 * only signed-up users can spend the budget.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

const STOP = new Set(
  "the a an and or of to in for on with is are was were do does what which how many our we us my me it this that from by as at be have has".split(
    " ",
  ),
);

function keywords(q: string): string[] {
  return Array.from(
    new Set(
      q
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, " ")
        .split(/\s+/)
        .filter((w) => w.length > 3 && !STOP.has(w)),
    ),
  ).slice(0, 4);
}

interface LlmResult {
  text: string;
  provider: string;
}

const PROVIDERS: {
  name: string;
  kind: "openai" | "anthropic";
  url: string;
  keyEnv: string;
  model: string;
}[] = [
  {
    name: "groq",
    kind: "openai",
    url: "https://api.groq.com/openai/v1/chat/completions",
    keyEnv: "GROQ_API_KEY",
    model: "llama-3.3-70b-versatile",
  },
  {
    name: "cerebras",
    kind: "openai",
    url: "https://api.cerebras.ai/v1/chat/completions",
    keyEnv: "CEREBRAS_API_KEY",
    model: "gpt-oss-120b",
  },
  {
    name: "gemini",
    kind: "openai",
    url: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    keyEnv: "GEMINI_API_KEY",
    model: "gemini-2.5-flash",
  },
  {
    name: "mistral",
    kind: "openai",
    url: "https://api.mistral.ai/v1/chat/completions",
    keyEnv: "MISTRAL_API_KEY",
    model: "mistral-small-latest",
  },
  {
    name: "openrouter",
    kind: "openai",
    url: "https://openrouter.ai/api/v1/chat/completions",
    keyEnv: "OPENROUTER_API_KEY",
    model: "meta-llama/llama-3.3-70b-instruct:free",
  },
  // Last resort: cheap paid tier. Haiku with a bounded completion keeps the
  // worst-case cost per answer at well under a cent.
  {
    name: "anthropic",
    kind: "anthropic",
    url: "https://api.anthropic.com/v1/messages",
    keyEnv: "ANTHROPIC_API_KEY",
    model: "claude-haiku-4-5",
  },
];

async function completeFree(system: string, user: string): Promise<LlmResult> {
  let lastErr = "no provider configured";
  for (const p of PROVIDERS) {
    const key = process.env[p.keyEnv];
    if (!key) continue;
    try {
      const headers: Record<string, string> =
        p.kind === "anthropic"
          ? { "x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json" }
          : { Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
      const body =
        p.kind === "anthropic"
          ? { model: p.model, max_tokens: 1200, system, messages: [{ role: "user", content: user }] }
          : {
              model: p.model,
              max_tokens: 1200,
              messages: [
                { role: "system", content: system },
                { role: "user", content: user },
              ],
            };
      const resp = await fetch(p.url, { method: "POST", headers, body: JSON.stringify(body) });
      if (!resp.ok) {
        lastErr = `${p.name} ${resp.status}: ${(await resp.text()).slice(0, 160)}`;
        continue;
      }
      const data = await resp.json();
      const text =
        p.kind === "anthropic"
          ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (data.content ?? []).map((b: any) => b.text ?? "").join("")
          : (data.choices?.[0]?.message?.content ?? "");
      if (text) return { text, provider: p.name };
      lastErr = `${p.name}: empty completion`;
    } catch (e) {
      lastErr = `${p.name}: ${(e as Error).message.slice(0, 120)}`;
    }
  }
  throw new Error(lastErr);
}

export async function POST(req: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) return NextResponse.json({ detail: "not configured" }, { status: 503 });

  const authHeader = req.headers.get("authorization") ?? "";
  if (!authHeader.toLowerCase().startsWith("bearer ")) {
    return NextResponse.json({ detail: "sign in to use the Copilot" }, { status: 401 });
  }
  // Query with the caller's token so their row-level security applies.
  const supabase = createClient(url, anon, {
    global: { headers: { Authorization: authHeader } },
    auth: { persistSession: false },
  });
  const {
    data: { user },
  } = await supabase.auth.getUser(authHeader.slice(7));
  if (!user) return NextResponse.json({ detail: "invalid session" }, { status: 401 });

  const { question } = (await req.json().catch(() => ({}))) as { question?: string };
  if (!question?.trim()) return NextResponse.json({ detail: "question required" }, { status: 422 });

  // ---- grounding: the caller's compliance state + relevant regulations ----
  const [obl, gaps, tasks] = await Promise.all([
    supabase.from("obligations").select("title, severity, status").limit(1000),
    supabase.from("gaps").select("description, severity, status, remediation_plan").limit(400),
    supabase.from("tasks").select("title, status, due_date").limit(400),
  ]);

  const terms = keywords(question);
  let regs: { title: string; source_url: string | null; regulator: string | null; summary: string | null }[] = [];
  if (terms.length) {
    const ors = terms
      .map((t) => `properties->>title.ilike.%${t}%,properties->>summary.ilike.%${t}%`)
      .join(",");
    const { data } = await supabase
      .from("nodes")
      .select("properties")
      .eq("node_type", "regulation")
      .or(ors)
      .limit(6);
    regs =
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (data ?? []).map((r: any) => ({
        title: r.properties?.title ?? "?",
        source_url: r.properties?.source_url ?? null,
        regulator: r.properties?.regulator ?? null,
        summary: (r.properties?.summary ?? "").slice(0, 350),
      }));
  }

  const today = new Date().toISOString().slice(0, 10);
  const oblRows = obl.data ?? [];
  const gapRows = gaps.data ?? [];
  const taskRows = tasks.data ?? [];
  const bySev = (rows: { severity?: string | null }[]) => {
    const c: Record<string, number> = {};
    rows.forEach((r) => (c[r.severity ?? "?"] = (c[r.severity ?? "?"] ?? 0) + 1));
    return c;
  };

  const grounding = {
    as_of: today,
    obligations: {
      total: oblRows.length,
      open: oblRows.filter((o) => o.status === "open").length,
      by_severity: bySev(oblRows.filter((o) => o.status === "open")),
      top_open_high: oblRows
        .filter((o) => o.status === "open" && ["critical", "high"].includes(o.severity ?? ""))
        .slice(0, 10)
        .map((o) => o.title),
    },
    gaps: {
      open: gapRows.filter((g) => g.status !== "closed").length,
      by_severity: bySev(gapRows.filter((g) => g.status !== "closed")),
      examples: gapRows
        .filter((g) => g.status !== "closed")
        .slice(0, 8)
        .map((g) => ({ description: g.description?.slice(0, 160), plan: g.remediation_plan?.slice(0, 120) })),
    },
    tasks: {
      open: taskRows.filter((t) => t.status !== "done").length,
      overdue: taskRows.filter((t) => t.status !== "done" && t.due_date && t.due_date < today).length,
    },
    relevant_regulations: regs.map((r) => ({ title: r.title, regulator: r.regulator, summary: r.summary })),
  };

  const system =
    "You are PolicyAI, a regulatory-compliance analyst for Indian financial-sector firms. " +
    "Answer ONLY from the GROUNDING DATA provided; if it does not cover the question, say so " +
    "plainly instead of guessing. Cite regulations by their exact title when you rely on them. " +
    "Format as clean GitHub-flavored markdown: open with a one-line bold bottom line, use short " +
    "'### ' headings for multi-part answers, bullet lists, and a compact table when comparing 3+ " +
    "items. Bold key figures and dates. Never emit a wall of prose.";

  try {
    const { text, provider } = await completeFree(
      system,
      `QUESTION: ${question}\n\nGROUNDING DATA (the firm's live compliance state):\n${JSON.stringify(grounding, null, 1)}`,
    );
    return NextResponse.json({
      answer: text,
      engine: provider,
      citations: regs
        .filter((r) => r.source_url)
        .map((r) => ({ title: r.title, source_url: r.source_url, source: r.regulator ?? "reg" })),
    });
  } catch (e) {
    return NextResponse.json(
      { detail: `backup Copilot unavailable: ${(e as Error).message}` },
      { status: 502 },
    );
  }
}
