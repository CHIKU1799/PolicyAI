import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * One compliance score, one formula, everywhere. The sidebar used to show
 * "% of controls effective" while the dashboard hero showed a weighted
 * posture, so the same screen could say 50/100 and 23/100 at once. Both now
 * call this. Inputs come from exact count queries, not row fetches, because
 * PostgREST caps un-ranged selects at 1,000 rows and silently skews every
 * count derived from them once a table outgrows that.
 */

export interface PostureInputs {
  controlsTotal: number;
  controlsEffective: number;
  obligationsTotal: number;
  obligationsCovered: number;
  openGaps: number;
}

export function postureScore(i: PostureInputs): number {
  const effectivePct = i.controlsTotal
    ? Math.round((i.controlsEffective / i.controlsTotal) * 100)
    : 0;
  const coveragePct = i.obligationsTotal
    ? Math.round((i.obligationsCovered / i.obligationsTotal) * 100)
    : 0;
  const gapTerm = i.obligationsTotal
    ? 100 - Math.min(100, (i.openGaps / i.obligationsTotal) * 100)
    : 100;
  return Math.round(0.45 * effectivePct + 0.35 * coveragePct + 0.2 * gapTerm) || 0;
}

export async function fetchPostureInputs(supabase: SupabaseClient): Promise<PostureInputs> {
  const [ct, ce, ot, oc, og] = await Promise.all([
    supabase.from("controls").select("id", { count: "exact", head: true }),
    supabase
      .from("controls")
      .select("id", { count: "exact", head: true })
      .eq("effectiveness", "effective"),
    supabase.from("obligations").select("id", { count: "exact", head: true }),
    supabase.from("obligation_controls").select("obligation_id"),
    supabase
      .from("gaps")
      .select("id", { count: "exact", head: true })
      .in("status", ["open", "remediating"]),
  ]);
  const covered = new Set(
    (((oc.data as { obligation_id: string }[] | null) ?? []).map((r) => r.obligation_id)),
  );
  return {
    controlsTotal: ct.count ?? 0,
    controlsEffective: ce.count ?? 0,
    obligationsTotal: ot.count ?? 0,
    obligationsCovered: covered.size,
    openGaps: og.count ?? 0,
  };
}
