import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * The single source of org-wide numbers, and the naming contract behind them.
 * Every headline figure on the dashboard, workflow, gaps and tasks pages comes
 * from here via exact count queries, because PostgREST caps plain selects at
 * 1,000 rows and silently skews any count derived from fetched rows once a
 * table outgrows that (open gaps read 954 on one page and 913 on another).
 *
 * Vocabulary, used consistently in the UI:
 * - "obligations": valid obligations (not invalidated). One number everywhere.
 * - "control coverage": % of obligations with at least one linked control.
 * - "requirement coverage": % of applicable requirements covered (worker
 *   /insights owns this; it is a different, finer-grained metric).
 * - "gaps resolved": status closed or accepted. "open" = open + remediating.
 * - "compliance score": the weighted posture below. Null until the workspace
 *   has data (a brand-new org must not start at 20/100 for doing nothing).
 */

export interface OrgCounts {
  obligations: number;
  obligationsOpen: number;
  obligationsCovered: number;
  gapsOpen: number; // open + remediating
  gapsUrgentOpen: number; // open + remediating, severity critical/high
  gapsResolved: number; // closed + accepted
  gapsTotal: number;
  gapsNew7d: number;
  tasksByStatus: Record<string, number>;
  tasksOverdue: number;
  controls: number;
  controlsEffective: number;
  controlsUntested: number;
  alerts30d: number; // customer-visible kinds only (scan_failed excluded)
}

const count = async (q: PromiseLike<{ count: number | null }>) => (await q).count ?? 0;

export async function fetchOrgCounts(supabase: SupabaseClient): Promise<OrgCounts> {
  const head = { count: "exact" as const, head: true };
  const iso7d = new Date(Date.now() - 7 * 864e5).toISOString();
  const iso30d = new Date(Date.now() - 30 * 864e5).toISOString();
  const today = new Date().toISOString().slice(0, 10);

  const [
    obligations,
    obligationsOpen,
    coveredRows,
    gapsOpen,
    gapsUrgentOpen,
    gapsResolved,
    gapsTotal,
    gapsNew7d,
    taskStatusPairs,
    tasksOverdue,
    controls,
    controlsEffective,
    controlsUntested,
    alerts30d,
  ] = await Promise.all([
    count(supabase.from("obligations").select("id", head).is("invalidated_at", null)),
    count(
      supabase.from("obligations").select("id", head).is("invalidated_at", null).eq("status", "open"),
    ),
    supabase.from("obligation_controls").select("obligation_id"),
    count(supabase.from("gaps").select("id", head).in("status", ["open", "remediating"])),
    count(
      supabase
        .from("gaps")
        .select("id", head)
        .in("status", ["open", "remediating"])
        .in("severity", ["critical", "high"]),
    ),
    count(supabase.from("gaps").select("id", head).in("status", ["closed", "accepted"])),
    count(supabase.from("gaps").select("id", head)),
    count(supabase.from("gaps").select("id", head).gte("created_at", iso7d)),
    Promise.all(
      ["todo", "in_progress", "blocked", "done"].map(async (s) => [
        s,
        await count(supabase.from("tasks").select("id", head).eq("status", s)),
      ]),
    ) as Promise<[string, number][]>,
    count(
      supabase
        .from("tasks")
        .select("id", head)
        .neq("status", "done")
        .not("due_date", "is", null)
        .lt("due_date", today),
    ),
    count(supabase.from("controls").select("id", head)),
    count(supabase.from("controls").select("id", head).eq("effectiveness", "effective")),
    count(supabase.from("controls").select("id", head).eq("effectiveness", "untested")),
    count(
      supabase
        .from("alerts")
        .select("id", head)
        .neq("kind", "scan_failed")
        .gte("created_at", iso30d),
    ),
  ]);

  const covered = new Set(
    (((coveredRows.data as { obligation_id: string }[] | null) ?? []).map((r) => r.obligation_id)),
  );
  const tasksByStatus: Record<string, number> = Object.fromEntries(taskStatusPairs);

  return {
    obligations,
    obligationsOpen,
    obligationsCovered: covered.size,
    gapsOpen,
    gapsUrgentOpen,
    gapsResolved,
    gapsTotal,
    gapsNew7d,
    tasksByStatus,
    tasksOverdue,
    controls,
    controlsEffective,
    controlsUntested,
    alerts30d,
  };
}

/** Weighted compliance score; null while the workspace has nothing to score. */
export function postureScore(c: OrgCounts): number | null {
  if (c.obligations === 0 && c.controls === 0) return null;
  const effectivePct = c.controls ? Math.round((c.controlsEffective / c.controls) * 100) : 0;
  const coveragePct = c.obligations ? Math.round((c.obligationsCovered / c.obligations) * 100) : 0;
  const gapTerm = c.obligations ? 100 - Math.min(100, (c.gapsOpen / c.obligations) * 100) : 100;
  return Math.round(0.45 * effectivePct + 0.35 * coveragePct + 0.2 * gapTerm) || 0;
}
