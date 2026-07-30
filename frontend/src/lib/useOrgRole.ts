"use client";

import { useEffect, useState } from "react";
import { getSupabase } from "@/lib/supabase";

export type OrgRole = "admin" | "member" | null;

// Module-level cache: the role is fetched once per session, no matter how many
// components mount the hook (sidebar + page guards would otherwise refetch).
let cachedRole: OrgRole | undefined;
let inflight: Promise<OrgRole> | null = null;

async function fetchRole(): Promise<OrgRole> {
  const supabase = getSupabase();
  if (!supabase) return null;
  const { data } = await supabase.auth.getUser();
  const uid = data.user?.id;
  if (!uid) return null;

  const { data: memberships } = await supabase
    .from("memberships")
    .select("role, created_at")
    .eq("user_id", uid)
    .order("created_at", { ascending: true })
    .limit(1);
  const role = memberships?.[0]?.role as string | undefined;
  if (role === "admin") return "admin";
  if (role) return "member";

  // Platform admins may have no org membership at all; treat them as admins so
  // nothing in the app is hidden from operators.
  const { data: pa } = await supabase
    .from("platform_admins")
    .select("user_id")
    .maybeSingle();
  return pa ? "admin" : null;
}

/**
 * The caller's role in their org: "admin", "member", or null when
 * unauthenticated or Supabase is not configured. Cached per session.
 */
export function useOrgRole(): { role: OrgRole; loading: boolean } {
  const [role, setRole] = useState<OrgRole>(cachedRole ?? null);
  const [loading, setLoading] = useState(cachedRole === undefined);

  useEffect(() => {
    if (cachedRole !== undefined) {
      setRole(cachedRole);
      setLoading(false);
      return;
    }
    if (!inflight) {
      inflight = fetchRole().then((r) => {
        cachedRole = r;
        return r;
      });
    }
    let alive = true;
    inflight.then((r) => {
      if (alive) {
        setRole(r);
        setLoading(false);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  return { role, loading };
}
